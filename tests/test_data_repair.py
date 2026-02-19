"""Tests for DataRepairer."""

from __future__ import annotations

from pathlib import Path

import pytest

from notebook_processor.ingestion.data_repair import DataRepairer
from notebook_processor.ingestion.transformations import TransformationLogger
from notebook_processor.models import Asset, AssetType, DataQualityIssue


@pytest.fixture
def repairer() -> DataRepairer:
    return DataRepairer()


@pytest.fixture
def xform_logger() -> TransformationLogger:
    return TransformationLogger()


def _make_asset(rel_path: str, fmt: str = "csv") -> Asset:
    return Asset(
        path=rel_path,
        type=AssetType.DATA,
        format=fmt,
        size_bytes=0,
    )


class TestEncodingRepair:
    def test_utf8_unchanged(
        self,
        repairer: DataRepairer,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        asset = _make_asset("data.csv")
        result = repairer.repair(asset, tmp_path, xform_logger)
        assert len(result.transformations) == 0
        assert len(xform_logger.entries) == 0

    def test_windows_1252_converted(
        self,
        repairer: DataRepairer,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        # Windows-1252 smart quotes: 0x92 = ', 0x93 = ", 0x94 = ", 0x96 = –, 0x97 = —
        raw = b"name,desc\nCaf\xe9,The team\x92s best\n"
        (tmp_path / "data.csv").write_bytes(raw)
        asset = _make_asset("data.csv")
        result = repairer.repair(asset, tmp_path, xform_logger)

        # Should have encoding transformation
        enc_xforms = [
            t for t in result.transformations if t.issue == DataQualityIssue.ENCODING
        ]
        assert len(enc_xforms) == 1
        assert "UTF-8" in enc_xforms[0].action

        # File should now be valid UTF-8
        text = (tmp_path / "data.csv").read_text(encoding="utf-8")
        assert "Café" in text
        assert "\u2019" in text  # RIGHT SINGLE QUOTATION MARK

        # Original preserved
        assert (tmp_path / "data.csv.orig").exists()
        assert (tmp_path / "data.csv.orig").read_bytes() == raw

    def test_backup_path_recorded(
        self,
        repairer: DataRepairer,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "data.csv").write_bytes(b"x\nCaf\xe9\n")
        asset = _make_asset("data.csv")
        result = repairer.repair(asset, tmp_path, xform_logger)
        enc_xforms = [
            t for t in result.transformations if t.issue == DataQualityIssue.ENCODING
        ]
        assert len(enc_xforms) == 1
        assert enc_xforms[0].backup_path == "data.csv.orig"

    def test_logger_receives_entries(
        self,
        repairer: DataRepairer,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "data.csv").write_bytes(b"x\nCaf\xe9\n")
        asset = _make_asset("data.csv")
        repairer.repair(asset, tmp_path, xform_logger)
        assert len(xform_logger.entries) >= 1
        assert xform_logger.entries[0].issue == DataQualityIssue.ENCODING

    def test_missing_file_returns_unchanged(
        self,
        repairer: DataRepairer,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        asset = _make_asset("nonexistent.csv")
        result = repairer.repair(asset, tmp_path, xform_logger)
        assert result == asset


class TestLineEndingRepair:
    def test_crlf_normalized(
        self,
        repairer: DataRepairer,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "data.csv").write_bytes(b"a,b\r\n1,2\r\n3,4\r\n")
        asset = _make_asset("data.csv")
        result = repairer.repair(asset, tmp_path, xform_logger)

        le_xforms = [
            t
            for t in result.transformations
            if t.issue == DataQualityIssue.LINE_ENDINGS
        ]
        assert len(le_xforms) == 1
        assert le_xforms[0].records_affected == 3

        content = (tmp_path / "data.csv").read_bytes()
        assert b"\r\n" not in content
        assert content == b"a,b\n1,2\n3,4\n"

    def test_lf_unchanged(
        self,
        repairer: DataRepairer,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "data.csv").write_bytes(b"a,b\n1,2\n")
        asset = _make_asset("data.csv")
        result = repairer.repair(asset, tmp_path, xform_logger)
        le_xforms = [
            t
            for t in result.transformations
            if t.issue == DataQualityIssue.LINE_ENDINGS
        ]
        assert len(le_xforms) == 0


class TestCombinedRepair:
    def test_encoding_and_line_endings(
        self,
        repairer: DataRepairer,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        # Build a CRLF-only UTF-8 file (no encoding issue, just line endings)
        # Then verify both repairs can apply independently
        crlf_data = b"id,name,score\r\n1,Alice,95\r\n2,Bob,80\r\n"
        (tmp_path / "crlf.csv").write_bytes(crlf_data)
        asset = _make_asset("crlf.csv")
        result = repairer.repair(asset, tmp_path, xform_logger)

        le_xforms = [
            t
            for t in result.transformations
            if t.issue == DataQualityIssue.LINE_ENDINGS
        ]
        assert len(le_xforms) == 1
        content = (tmp_path / "crlf.csv").read_bytes()
        assert b"\r\n" not in content

    def test_fixture_csv(
        self,
        repairer: DataRepairer,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        """Test against real fixture (Windows-1252 encoded)."""
        fixture = Path(__file__).parent / "fixtures" / "ingestion" / "fixture_data.csv"
        if not fixture.exists():
            pytest.skip("fixture not available")

        # Copy fixture into tmp_path for repair
        dest = tmp_path / "fixture_data.csv"
        dest.write_bytes(fixture.read_bytes())

        asset = _make_asset("fixture_data.csv")
        result = repairer.repair(asset, tmp_path, xform_logger)

        # Should detect encoding issue
        enc_xforms = [
            t for t in result.transformations if t.issue == DataQualityIssue.ENCODING
        ]
        assert len(enc_xforms) == 1

        # File should now be valid UTF-8
        text = dest.read_text(encoding="utf-8")
        assert "Café" in text or "Résumé" in text or "team" in text
