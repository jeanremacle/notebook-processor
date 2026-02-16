"""Tests for notebook_processor.solver."""

from __future__ import annotations

from unittest.mock import patch

from notebook_processor.models import (
    CellStatus,
    CellType,
    NotebookCell,
    NotebookContent,
)
from notebook_processor.solver import ManualSolver, StubSolver


def _make_content(cells: list[NotebookCell]) -> NotebookContent:
    return NotebookContent(path="test.ipynb", cells=cells, metadata={})


class TestStubSolver:
    def test_solve_code_cell(self) -> None:
        solver = StubSolver()
        cell = NotebookCell(
            index=0,
            cell_type=CellType.CODE,
            source="# TODO\nraise NotImplementedError",
            status=CellStatus.TODO_CODE,
        )
        content = _make_content([cell])
        result = solver.solve_code_cell(cell, content)
        assert "pass" in result

    def test_solve_markdown_cell(self) -> None:
        solver = StubSolver()
        cell = NotebookCell(
            index=0,
            cell_type=CellType.MARKDOWN,
            source="**Your answer here:**",
            status=CellStatus.TODO_MARKDOWN,
        )
        content = _make_content([cell])
        result = solver.solve_markdown_cell(cell, content)
        assert "placeholder" in result.lower()

    def test_solve_all_cells(self) -> None:
        solver = StubSolver()
        cells = [
            NotebookCell(
                index=0,
                cell_type=CellType.MARKDOWN,
                source="# Intro",
                status=CellStatus.ORIGINAL,
            ),
            NotebookCell(
                index=1,
                cell_type=CellType.CODE,
                source="# TODO",
                status=CellStatus.TODO_CODE,
            ),
            NotebookCell(
                index=2,
                cell_type=CellType.MARKDOWN,
                source="**Your answer here:**",
                status=CellStatus.TODO_MARKDOWN,
            ),
            NotebookCell(
                index=3,
                cell_type=CellType.CODE,
                source="print('ok')",
                status=CellStatus.ORIGINAL,
            ),
        ]
        content = _make_content(cells)
        result = solver.solve(content)

        assert result.cells[0].status == CellStatus.ORIGINAL
        assert result.cells[0].source == "# Intro"

        assert result.cells[1].status == CellStatus.COMPLETED
        assert result.cells[1].original_source == "# TODO"
        assert "pass" in result.cells[1].source

        assert result.cells[2].status == CellStatus.COMPLETED
        assert result.cells[2].original_source == "**Your answer here:**"

        assert result.cells[3].status == CellStatus.ORIGINAL

    def test_solve_preserves_original_content(self) -> None:
        solver = StubSolver()
        cells = [
            NotebookCell(
                index=0,
                cell_type=CellType.CODE,
                source="x = 1",
                status=CellStatus.ORIGINAL,
            ),
        ]
        content = _make_content(cells)
        result = solver.solve(content)
        assert result.cells[0].source == "x = 1"
        assert result.cells[0].original_source is None


class TestManualSolver:
    def test_solve_code_cell(self) -> None:
        solver = ManualSolver()
        cell = NotebookCell(
            index=0,
            cell_type=CellType.CODE,
            source="# TODO",
            status=CellStatus.TODO_CODE,
        )
        content = _make_content([cell])
        with patch("builtins.input", side_effect=["x = 42", ""]):
            result = solver.solve_code_cell(cell, content)
        assert result == "x = 42"

    def test_solve_markdown_cell(self) -> None:
        solver = ManualSolver()
        cell = NotebookCell(
            index=0,
            cell_type=CellType.MARKDOWN,
            source="Q?",
            status=CellStatus.TODO_MARKDOWN,
        )
        content = _make_content([cell])
        with patch("builtins.input", side_effect=["My answer", "line 2", ""]):
            result = solver.solve_markdown_cell(cell, content)
        assert result == "My answer\nline 2"

    def test_solve_multiline(self) -> None:
        solver = ManualSolver()
        cell = NotebookCell(
            index=0,
            cell_type=CellType.CODE,
            source="# TODO",
            status=CellStatus.TODO_CODE,
        )
        content = _make_content([cell])
        lines = ["def f():", "    return 1", ""]
        with patch("builtins.input", side_effect=lines):
            result = solver.solve_code_cell(cell, content)
        assert result == "def f():\n    return 1"
