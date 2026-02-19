"""Tests for ManifestGenerator."""

from __future__ import annotations

import json
from pathlib import Path

from notebook_processor.ingestion.manifest_generator import ManifestGenerator
from notebook_processor.models import (
    Asset,
    AssetType,
    NotebookAnalysis,
    PackageManifest,
)


def _make_analysis() -> NotebookAnalysis:
    return NotebookAnalysis(
        total_cells=5,
        cell_type_counts={"code": 3, "markdown": 2},
        todo_markers=[],
        embedded_images_count=0,
        embedded_images_total_bytes=0,
        kernel_spec="python3",
    )


def _make_assets() -> list[Asset]:
    return [
        Asset(
            path="hw1.ipynb",
            type=AssetType.NOTEBOOK,
            format="ipynb",
            size_bytes=1024,
        ),
        Asset(
            path="data.csv",
            type=AssetType.DATA,
            format="csv",
            size_bytes=512,
        ),
    ]


class TestManifestGenerator:
    def test_generates_manifest(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "test-package"
        pkg_dir.mkdir()

        gen = ManifestGenerator()
        manifest = gen.generate(pkg_dir, _make_assets(), _make_analysis())

        assert isinstance(manifest, PackageManifest)
        assert manifest.package.id == "test-package"
        assert manifest.package.status == "pending"

    def test_writes_manifest_json(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "hw1-assignment"
        pkg_dir.mkdir()

        gen = ManifestGenerator()
        gen.generate(pkg_dir, _make_assets(), _make_analysis())

        manifest_path = pkg_dir / "manifest.json"
        assert manifest_path.exists()

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["package"]["id"] == "hw1-assignment"
        assert len(data["assets"]) == 2

    def test_notebook_metadata(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        gen = ManifestGenerator()
        manifest = gen.generate(pkg_dir, _make_assets(), _make_analysis())

        assert manifest.notebook.filename == "notebook.ipynb"
        assert manifest.notebook.original_filename == "hw1.ipynb"
        assert manifest.notebook.kernel == "python3"
        assert manifest.notebook.analysis is not None
        assert manifest.notebook.analysis.total_cells == 5

    def test_package_name_from_dir(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "w9-email-prioritization"
        pkg_dir.mkdir()

        gen = ManifestGenerator()
        manifest = gen.generate(pkg_dir, _make_assets(), _make_analysis())

        assert manifest.package.name == "W9 Email Prioritization"

    def test_created_at_is_iso(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        gen = ManifestGenerator()
        manifest = gen.generate(pkg_dir, _make_assets(), _make_analysis())

        # Should be parseable ISO 8601
        assert "T" in manifest.package.created_at

    def test_manifest_roundtrip(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        gen = ManifestGenerator()
        manifest = gen.generate(pkg_dir, _make_assets(), _make_analysis())

        # Validate by re-parsing the JSON
        manifest_path = pkg_dir / "manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        restored = PackageManifest.model_validate(data)
        assert restored.package.id == manifest.package.id
        assert len(restored.assets) == len(manifest.assets)

    def test_empty_improvements(self, tmp_path: Path) -> None:
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        gen = ManifestGenerator()
        manifest = gen.generate(
            pkg_dir, _make_assets(), _make_analysis(), improvements=[]
        )
        assert manifest.instruction_improvements == []

    def test_no_notebook_asset(self, tmp_path: Path) -> None:
        """If no notebook asset, falls back to default filename."""
        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        assets = [
            Asset(
                path="data.csv",
                type=AssetType.DATA,
                format="csv",
                size_bytes=100,
            )
        ]
        gen = ManifestGenerator()
        manifest = gen.generate(pkg_dir, assets, _make_analysis())
        assert manifest.notebook.original_filename == "notebook.ipynb"
