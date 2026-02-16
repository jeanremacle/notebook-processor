"""Tests for notebook_processor.builder."""

from __future__ import annotations

from pathlib import Path

import nbformat

from notebook_processor.builder import NotebookBuilder
from notebook_processor.models import (
    CellStatus,
    CellType,
    NotebookCell,
    NotebookContent,
)
from notebook_processor.parser import NotebookParser


def _make_content(
    cells: list[NotebookCell],
    metadata: dict[str, object] | None = None,
) -> NotebookContent:
    return NotebookContent(
        path="test.ipynb",
        cells=cells,
        metadata=metadata or {},
    )


class TestNotebookBuilder:
    def test_build_creates_file(self, tmp_output: Path) -> None:
        builder = NotebookBuilder()
        content = _make_content(
            [
                NotebookCell(index=0, cell_type=CellType.CODE, source="x = 1"),
            ]
        )
        out = builder.build(content, tmp_output / "result.ipynb")
        assert out.exists()
        assert out.suffix == ".ipynb"

    def test_build_creates_parent_dirs(self, tmp_path: Path) -> None:
        builder = NotebookBuilder()
        content = _make_content(
            [
                NotebookCell(index=0, cell_type=CellType.CODE, source="x = 1"),
            ]
        )
        out = builder.build(content, tmp_path / "sub" / "dir" / "result.ipynb")
        assert out.exists()

    def test_build_preserves_cell_sources(self, tmp_output: Path) -> None:
        builder = NotebookBuilder()
        content = _make_content(
            [
                NotebookCell(index=0, cell_type=CellType.CODE, source="x = 1"),
                NotebookCell(index=1, cell_type=CellType.MARKDOWN, source="# Hello"),
            ]
        )
        out = builder.build(content, tmp_output / "result.ipynb")
        nb = nbformat.read(str(out), as_version=4)
        assert nb.cells[0].source == "x = 1"
        assert nb.cells[1].source == "# Hello"

    def test_build_preserves_cell_types(self, tmp_output: Path) -> None:
        builder = NotebookBuilder()
        content = _make_content(
            [
                NotebookCell(index=0, cell_type=CellType.CODE, source="x = 1"),
                NotebookCell(index=1, cell_type=CellType.MARKDOWN, source="# Title"),
                NotebookCell(index=2, cell_type=CellType.RAW, source="raw text"),
            ]
        )
        out = builder.build(content, tmp_output / "result.ipynb")
        nb = nbformat.read(str(out), as_version=4)
        assert nb.cells[0].cell_type == "code"
        assert nb.cells[1].cell_type == "markdown"
        assert nb.cells[2].cell_type == "raw"

    def test_build_clears_outputs_for_completed_cells(self, tmp_output: Path) -> None:
        builder = NotebookBuilder()
        content = _make_content(
            [
                NotebookCell(
                    index=0,
                    cell_type=CellType.CODE,
                    source="print('new')",
                    status=CellStatus.COMPLETED,
                    outputs=[{"output_type": "stream", "text": "old"}],
                ),
            ]
        )
        out = builder.build(content, tmp_output / "result.ipynb")
        nb = nbformat.read(str(out), as_version=4)
        assert len(nb.cells[0].outputs) == 0

    def test_build_preserves_outputs_for_original_cells(self, tmp_output: Path) -> None:
        builder = NotebookBuilder()
        content = _make_content(
            [
                NotebookCell(
                    index=0,
                    cell_type=CellType.CODE,
                    source="print('hi')",
                    status=CellStatus.ORIGINAL,
                    outputs=[{"output_type": "stream", "text": "hi", "name": "stdout"}],
                ),
            ]
        )
        out = builder.build(content, tmp_output / "result.ipynb")
        nb = nbformat.read(str(out), as_version=4)
        assert len(nb.cells[0].outputs) == 1

    def test_build_preserves_metadata(self, tmp_output: Path) -> None:
        builder = NotebookBuilder()
        meta = {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            }
        }
        content = _make_content(
            [NotebookCell(index=0, cell_type=CellType.CODE, source="x = 1")],
            metadata=meta,
        )
        out = builder.build(content, tmp_output / "result.ipynb")
        nb = nbformat.read(str(out), as_version=4)
        assert nb.metadata["kernelspec"]["name"] == "python3"

    def test_roundtrip_parse_build_parse(
        self, fixtures_dir: Path, tmp_output: Path
    ) -> None:
        """Parse → build → parse again and verify structure is preserved."""
        parser = NotebookParser()
        builder = NotebookBuilder()

        original = parser.parse(fixtures_dir)
        out_path = tmp_output / "roundtrip.ipynb"
        builder.build(original, out_path)

        reparsed = parser.parse(tmp_output)
        assert len(reparsed.cells) == len(original.cells)
        for orig, re_cell in zip(original.cells, reparsed.cells, strict=True):
            assert orig.cell_type == re_cell.cell_type
            assert orig.source == re_cell.source

    def test_build_valid_notebook(self, tmp_output: Path) -> None:
        """Verify the output is a valid nbformat notebook."""
        builder = NotebookBuilder()
        content = _make_content(
            [
                NotebookCell(index=0, cell_type=CellType.CODE, source="x = 1"),
            ]
        )
        out = builder.build(content, tmp_output / "result.ipynb")
        nb = nbformat.read(str(out), as_version=4)
        nbformat.validate(nb)
