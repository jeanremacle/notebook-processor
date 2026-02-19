"""Tests for PackageIngestor."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from notebook_processor.ingestion.ingestor import PackageIngestor
from notebook_processor.models import PackageManifest


@pytest.fixture
def ingestor() -> PackageIngestor:
    return PackageIngestor()


def _minimal_png_b64() -> str:
    """Return base64 of a minimal valid PNG (1x1 pixel)."""
    return base64.b64encode(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    ).decode()


def _make_raw_dir(tmp_path: Path) -> Path:
    """Create a raw assignment directory mimicking a JHU notebook."""
    raw = tmp_path / "raw"
    raw.mkdir()

    # Notebook with a TODO marker and a base64 image in output
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3",
                "language": "python",
            }
        },
        "cells": [
            {
                "cell_type": "markdown",
                "source": "# Assignment 1",
                "metadata": {},
                "id": "cell-md-1",
            },
            {
                "cell_type": "code",
                "source": 'system_prompt = "<-- YOUR SYSTEM PROMPT GOES HERE -->"',
                "metadata": {},
                "execution_count": None,
                "id": "cell-code-1",
                "outputs": [],
            },
            {
                "cell_type": "code",
                "source": "import openai\nimport pandas",
                "metadata": {},
                "execution_count": 1,
                "id": "cell-code-2",
                "outputs": [
                    {
                        "output_type": "display_data",
                        "data": {"image/png": _minimal_png_b64()},
                        "metadata": {},
                    }
                ],
            },
            {
                "cell_type": "code",
                "source": 'df = pd.read_csv("your_file_location")',
                "metadata": {},
                "execution_count": 2,
                "id": "cell-code-3",
                "outputs": [],
            },
        ],
    }
    (raw / "homework.ipynb").write_text(json.dumps(nb), encoding="utf-8")

    # CSV with Windows-1252 encoding
    (raw / "data.csv").write_bytes(
        b"id,name,description\n"
        b"1,Caf\xe9 Project,The team\x92s best effort\n"
        b"2,Na\xefve Approach,Don\x92t underestimate\n"
    )

    # Instructions
    (raw / "instructions.md").write_text(
        "# Homework 1\n\nComplete the TODO cells.\n",
        encoding="utf-8",
    )

    return raw


class TestPackageIngestor:
    def test_ingest_creates_manifest(
        self, ingestor: PackageIngestor, tmp_path: Path
    ) -> None:
        raw = _make_raw_dir(tmp_path)
        target = tmp_path / "pkg"

        manifest = ingestor.ingest(raw, target)

        assert isinstance(manifest, PackageManifest)
        assert (target / "manifest.json").exists()

    def test_ingest_copies_files(
        self, ingestor: PackageIngestor, tmp_path: Path
    ) -> None:
        raw = _make_raw_dir(tmp_path)
        target = tmp_path / "pkg"

        ingestor.ingest(raw, target)

        assert (target / "homework.ipynb").exists() or (
            target / "notebook.ipynb"
        ).exists()
        assert (target / "data.csv").exists()
        assert (target / "instructions.md").exists()

    def test_ingest_repairs_encoding(
        self, ingestor: PackageIngestor, tmp_path: Path
    ) -> None:
        raw = _make_raw_dir(tmp_path)
        target = tmp_path / "pkg"

        ingestor.ingest(raw, target)

        # CSV should now be UTF-8
        text = (target / "data.csv").read_text(encoding="utf-8")
        assert "Café" in text or "team" in text

        # Original should be preserved
        assert (target / "data.csv.orig").exists()

    def test_ingest_extracts_images(
        self, ingestor: PackageIngestor, tmp_path: Path
    ) -> None:
        raw = _make_raw_dir(tmp_path)
        target = tmp_path / "pkg"

        manifest = ingestor.ingest(raw, target)

        assert manifest.notebook.analysis is not None
        assert manifest.notebook.analysis.embedded_images_count >= 1
        assert (target / "images").is_dir()

    def test_ingest_detects_todo_markers(
        self, ingestor: PackageIngestor, tmp_path: Path
    ) -> None:
        raw = _make_raw_dir(tmp_path)
        target = tmp_path / "pkg"

        manifest = ingestor.ingest(raw, target)

        assert manifest.notebook.analysis is not None
        assert len(manifest.notebook.analysis.todo_markers) >= 1

    def test_ingest_detects_dependencies(
        self, ingestor: PackageIngestor, tmp_path: Path
    ) -> None:
        raw = _make_raw_dir(tmp_path)
        target = tmp_path / "pkg"

        manifest = ingestor.ingest(raw, target)

        assert manifest.notebook.analysis is not None
        assert "openai" in manifest.notebook.analysis.dependencies
        assert "openai" in manifest.notebook.analysis.api_dependencies

    def test_ingest_saves_transformations_log(
        self, ingestor: PackageIngestor, tmp_path: Path
    ) -> None:
        raw = _make_raw_dir(tmp_path)
        target = tmp_path / "pkg"

        ingestor.ingest(raw, target)

        log_path = target / "transformations.log"
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        assert len(content) > 0

    def test_ingest_saves_cleaned_notebook(
        self, ingestor: PackageIngestor, tmp_path: Path
    ) -> None:
        raw = _make_raw_dir(tmp_path)
        target = tmp_path / "pkg"

        ingestor.ingest(raw, target)

        assert (target / "notebook.ipynb").exists()
        assert (target / "notebook.ipynb.orig").exists()

    def test_ingest_nonexistent_dir(
        self, ingestor: PackageIngestor, tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError):
            ingestor.ingest(tmp_path / "nonexistent", tmp_path / "pkg")

    def test_ingest_no_notebook(
        self, ingestor: PackageIngestor, tmp_path: Path
    ) -> None:
        raw = tmp_path / "raw"
        raw.mkdir()
        (raw / "data.csv").write_text("a\n1\n", encoding="utf-8")

        with pytest.raises(FileNotFoundError, match="No notebook"):
            ingestor.ingest(raw, tmp_path / "pkg")

    def test_manifest_json_roundtrip(
        self, ingestor: PackageIngestor, tmp_path: Path
    ) -> None:
        raw = _make_raw_dir(tmp_path)
        target = tmp_path / "pkg"

        ingestor.ingest(raw, target)

        data = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        restored = PackageManifest.model_validate(data)
        assert restored.package.id == "pkg"
