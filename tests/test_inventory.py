"""Tests for InventoryScanner."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from notebook_processor.ingestion.inventory import InventoryScanner
from notebook_processor.models import AssetType


@pytest.fixture
def scanner() -> InventoryScanner:
    return InventoryScanner()


@pytest.fixture
def ingestion_fixtures() -> Path:
    return Path(__file__).parent / "fixtures" / "ingestion"


class TestInventoryScanner:
    def test_scan_empty_dir(self, scanner: InventoryScanner, tmp_path: Path) -> None:
        assets = scanner.scan(tmp_path)
        assert assets == []

    def test_scan_nonexistent_dir(
        self, scanner: InventoryScanner, tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError):
            scanner.scan(tmp_path / "nonexistent")

    def test_scan_classifies_notebook(
        self, scanner: InventoryScanner, tmp_path: Path
    ) -> None:
        (tmp_path / "test.ipynb").write_text("{}", encoding="utf-8")
        assets = scanner.scan(tmp_path)
        assert len(assets) == 1
        assert assets[0].type == AssetType.NOTEBOOK
        assert assets[0].format == "ipynb"

    def test_scan_classifies_csv(
        self, scanner: InventoryScanner, tmp_path: Path
    ) -> None:
        (tmp_path / "data.csv").write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
        assets = scanner.scan(tmp_path)
        assert len(assets) == 1
        assert assets[0].type == AssetType.DATA
        assert assets[0].format == "csv"

    def test_scan_classifies_tsv(
        self, scanner: InventoryScanner, tmp_path: Path
    ) -> None:
        (tmp_path / "data.tsv").write_text("a\tb\n1\t2\n", encoding="utf-8")
        assets = scanner.scan(tmp_path)
        assert len(assets) == 1
        assert assets[0].type == AssetType.DATA
        assert assets[0].format == "tsv"

    def test_scan_classifies_image(
        self, scanner: InventoryScanner, tmp_path: Path
    ) -> None:
        (tmp_path / "photo.png").write_bytes(b"\x89PNG\r\n")
        assets = scanner.scan(tmp_path)
        assert len(assets) == 1
        assert assets[0].type == AssetType.IMAGE

    def test_scan_classifies_instructions(
        self, scanner: InventoryScanner, tmp_path: Path
    ) -> None:
        (tmp_path / "readme.md").write_text("# Hi", encoding="utf-8")
        assets = scanner.scan(tmp_path)
        assert len(assets) == 1
        assert assets[0].type == AssetType.INSTRUCTIONS

    def test_scan_classifies_supplement(
        self, scanner: InventoryScanner, tmp_path: Path
    ) -> None:
        (tmp_path / "rubric.pdf").write_bytes(b"%PDF-1.4")
        assets = scanner.scan(tmp_path)
        assert len(assets) == 1
        assert assets[0].type == AssetType.SUPPLEMENT
        assert assets[0].format == "pdf"

    def test_scan_records_size(self, scanner: InventoryScanner, tmp_path: Path) -> None:
        content = "hello world"
        (tmp_path / "test.txt").write_text(content, encoding="utf-8")
        assets = scanner.scan(tmp_path)
        assert assets[0].size_bytes == len(content.encode("utf-8"))

    def test_scan_relative_paths(
        self, scanner: InventoryScanner, tmp_path: Path
    ) -> None:
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "nested.csv").write_text("a\n1\n", encoding="utf-8")
        assets = scanner.scan(tmp_path)
        assert assets[0].path == "subdir/nested.csv"

    def test_scan_multiple_files(
        self, scanner: InventoryScanner, tmp_path: Path
    ) -> None:
        (tmp_path / "nb.ipynb").write_text("{}", encoding="utf-8")
        (tmp_path / "data.csv").write_text("a\n1\n", encoding="utf-8")
        (tmp_path / "img.png").write_bytes(b"\x89PNG")
        (tmp_path / "instructions.md").write_text("# I", encoding="utf-8")
        assets = scanner.scan(tmp_path)
        assert len(assets) == 4
        types = {a.type for a in assets}
        assert types == {
            AssetType.NOTEBOOK,
            AssetType.DATA,
            AssetType.IMAGE,
            AssetType.INSTRUCTIONS,
        }

    def test_scan_sorted_output(
        self, scanner: InventoryScanner, tmp_path: Path
    ) -> None:
        (tmp_path / "b.txt").write_text("b", encoding="utf-8")
        (tmp_path / "a.txt").write_text("a", encoding="utf-8")
        assets = scanner.scan(tmp_path)
        assert assets[0].path == "a.txt"
        assert assets[1].path == "b.txt"


class TestCsvSchema:
    def test_csv_schema_extracted(
        self, scanner: InventoryScanner, tmp_path: Path
    ) -> None:
        (tmp_path / "data.csv").write_text(
            "id,name,score\n1,Alice,95\n2,Bob,80\n3,Carol,\n",
            encoding="utf-8",
        )
        assets = scanner.scan(tmp_path)
        schema = assets[0].schema_info
        assert schema is not None
        assert schema.columns == ["id", "name", "score"]
        assert schema.row_count == 3
        assert len(schema.sample_head) == 3
        assert len(schema.sample_tail) == 2
        assert "score" in schema.null_counts
        assert schema.null_counts["score"] == 1

    def test_csv_schema_dtypes(self, scanner: InventoryScanner, tmp_path: Path) -> None:
        (tmp_path / "data.csv").write_text("x,y\n1,hello\n2,world\n", encoding="utf-8")
        assets = scanner.scan(tmp_path)
        schema = assets[0].schema_info
        assert schema is not None
        assert "int" in schema.dtypes["x"]
        assert schema.dtypes["y"] == "object"

    def test_tsv_schema_extracted(
        self, scanner: InventoryScanner, tmp_path: Path
    ) -> None:
        (tmp_path / "data.tsv").write_text("col1\tcol2\n10\t20\n", encoding="utf-8")
        assets = scanner.scan(tmp_path)
        schema = assets[0].schema_info
        assert schema is not None
        assert schema.columns == ["col1", "col2"]
        assert schema.row_count == 1

    def test_fixture_csv(
        self, scanner: InventoryScanner, ingestion_fixtures: Path
    ) -> None:
        """Test against the real fixture_data.csv (Windows-1252)."""
        assets = scanner.scan(ingestion_fixtures)
        csv_assets = [a for a in assets if a.format == "csv"]
        assert len(csv_assets) == 1
        schema = csv_assets[0].schema_info
        assert schema is not None
        assert schema.row_count > 0


class TestZipContents:
    def test_zip_contents_listed(
        self, scanner: InventoryScanner, tmp_path: Path
    ) -> None:
        zip_path = tmp_path / "archive.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file1.txt", "hello")
            zf.writestr("subdir/file2.txt", "world")
        assets = scanner.scan(tmp_path)
        assert len(assets) == 1
        assert assets[0].type == AssetType.SUPPLEMENT
        assert assets[0].contents is not None
        assert "file1.txt" in assets[0].contents
        assert "subdir/file2.txt" in assets[0].contents

    def test_bad_zip_handled(self, scanner: InventoryScanner, tmp_path: Path) -> None:
        (tmp_path / "bad.zip").write_bytes(b"not a zip file")
        assets = scanner.scan(tmp_path)
        assert assets[0].contents is None
