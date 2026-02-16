"""Tests for notebook_processor.exporter."""

from __future__ import annotations

from pathlib import Path

import nbformat
import pytest

from notebook_processor.exporter import NotebookExporter


@pytest.fixture
def exporter() -> NotebookExporter:
    return NotebookExporter()


def _create_notebook(path: Path) -> Path:
    """Create a simple notebook for export testing."""
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_markdown_cell("# Test"))
    nb.cells.append(nbformat.v4.new_code_cell("print('hello')"))
    nbformat.write(nb, str(path))
    return path


class TestNotebookExporter:
    def test_export_creates_html(
        self, exporter: NotebookExporter, tmp_path: Path
    ) -> None:
        nb_path = _create_notebook(tmp_path / "test.ipynb")
        result = exporter.export_html(nb_path)
        assert result.exists()
        assert result.suffix == ".html"

    def test_export_default_output_path(
        self, exporter: NotebookExporter, tmp_path: Path
    ) -> None:
        nb_path = _create_notebook(tmp_path / "test.ipynb")
        result = exporter.export_html(nb_path)
        assert result == tmp_path / "test.html"

    def test_export_custom_output_path(
        self, exporter: NotebookExporter, tmp_path: Path
    ) -> None:
        nb_path = _create_notebook(tmp_path / "test.ipynb")
        out = tmp_path / "output" / "report.html"
        result = exporter.export_html(nb_path, out)
        assert result == out
        assert result.exists()

    def test_export_contains_html(
        self, exporter: NotebookExporter, tmp_path: Path
    ) -> None:
        nb_path = _create_notebook(tmp_path / "test.ipynb")
        result = exporter.export_html(nb_path)
        html = result.read_text(encoding="utf-8")
        assert "<html" in html.lower()
        assert "Test" in html

    def test_export_file_not_found(
        self, exporter: NotebookExporter, tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError):
            exporter.export_html(tmp_path / "nonexistent.ipynb")

    def test_export_creates_parent_dirs(
        self, exporter: NotebookExporter, tmp_path: Path
    ) -> None:
        nb_path = _create_notebook(tmp_path / "test.ipynb")
        out = tmp_path / "sub" / "dir" / "report.html"
        result = exporter.export_html(nb_path, out)
        assert result.exists()
