"""Tests for notebook_processor.parser."""

from __future__ import annotations

from pathlib import Path

import nbformat
import pytest

from notebook_processor.models import CellStatus, CellType
from notebook_processor.parser import NotebookParser


@pytest.fixture
def parser() -> NotebookParser:
    return NotebookParser()


class TestNotebookParser:
    def test_parse_finds_notebook(
        self, parser: NotebookParser, fixtures_dir: Path
    ) -> None:
        content = parser.parse(fixtures_dir)
        assert content.path.endswith(".ipynb")

    def test_parse_extracts_all_cells(
        self, parser: NotebookParser, fixtures_dir: Path
    ) -> None:
        content = parser.parse(fixtures_dir)
        assert len(content.cells) == 5

    def test_parse_detects_todo_code_cells(
        self, parser: NotebookParser, fixtures_dir: Path
    ) -> None:
        content = parser.parse(fixtures_dir)
        todo_code = [c for c in content.cells if c.status == CellStatus.TODO_CODE]
        assert len(todo_code) == 2

    def test_parse_detects_todo_markdown_cells(
        self, parser: NotebookParser, fixtures_dir: Path
    ) -> None:
        content = parser.parse(fixtures_dir)
        todo_md = [c for c in content.cells if c.status == CellStatus.TODO_MARKDOWN]
        assert len(todo_md) == 1

    def test_parse_original_cells(
        self, parser: NotebookParser, fixtures_dir: Path
    ) -> None:
        content = parser.parse(fixtures_dir)
        original = [c for c in content.cells if c.status == CellStatus.ORIGINAL]
        assert len(original) == 2

    def test_parse_cell_types(self, parser: NotebookParser, fixtures_dir: Path) -> None:
        content = parser.parse(fixtures_dir)
        code_cells = [c for c in content.cells if c.cell_type == CellType.CODE]
        md_cells = [c for c in content.cells if c.cell_type == CellType.MARKDOWN]
        assert len(code_cells) == 3
        assert len(md_cells) == 2

    def test_parse_extracts_kernel_spec(
        self, parser: NotebookParser, fixtures_dir: Path
    ) -> None:
        content = parser.parse(fixtures_dir)
        assert content.kernel_spec == "python3"

    def test_parse_loads_instructions(
        self, parser: NotebookParser, fixtures_dir: Path
    ) -> None:
        content = parser.parse(fixtures_dir)
        assert content.instructions is not None
        assert "Complete all TODO" in content.instructions.content

    def test_parse_no_notebook_raises(
        self, parser: NotebookParser, tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError, match=r"No \.ipynb file"):
            parser.parse(tmp_path)

    def test_parse_empty_code_cell_is_todo(
        self, parser: NotebookParser, tmp_path: Path
    ) -> None:
        nb = nbformat.v4.new_notebook()
        nb.cells.append(nbformat.v4.new_code_cell(""))
        nbformat.write(nb, str(tmp_path / "test.ipynb"))

        content = parser.parse(tmp_path)
        assert content.cells[0].status == CellStatus.TODO_CODE

    def test_parse_no_instructions(
        self, parser: NotebookParser, tmp_path: Path
    ) -> None:
        nb = nbformat.v4.new_notebook()
        nb.cells.append(nbformat.v4.new_code_cell("x = 1"))
        nbformat.write(nb, str(tmp_path / "test.ipynb"))

        content = parser.parse(tmp_path)
        assert content.instructions is None

    def test_parse_preserves_metadata(
        self, parser: NotebookParser, fixtures_dir: Path
    ) -> None:
        content = parser.parse(fixtures_dir)
        assert "kernelspec" in content.metadata

    def test_cell_indices_are_sequential(
        self, parser: NotebookParser, fixtures_dir: Path
    ) -> None:
        content = parser.parse(fixtures_dir)
        for i, cell in enumerate(content.cells):
            assert cell.index == i

    def test_parse_images_detected(
        self, parser: NotebookParser, tmp_path: Path
    ) -> None:
        nb = nbformat.v4.new_notebook()
        nb.cells.append(nbformat.v4.new_code_cell("x = 1"))
        nbformat.write(nb, str(tmp_path / "test.ipynb"))

        # Create instructions and images
        (tmp_path / "instructions.md").write_text("See image")
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        (images_dir / "output.png").write_bytes(b"fake png")

        content = parser.parse(tmp_path)
        assert content.instructions is not None
        assert len(content.instructions.images) == 1
        assert content.instructions.images[0].endswith("output.png")


class TestTodoDetection:
    """Test various TODO marker patterns."""

    def test_todo_comment(self, parser: NotebookParser, tmp_path: Path) -> None:
        nb = nbformat.v4.new_notebook()
        nb.cells.append(nbformat.v4.new_code_cell("# TODO: implement this"))
        nbformat.write(nb, str(tmp_path / "test.ipynb"))
        content = parser.parse(tmp_path)
        assert content.cells[0].status == CellStatus.TODO_CODE

    def test_your_code_here(self, parser: NotebookParser, tmp_path: Path) -> None:
        nb = nbformat.v4.new_notebook()
        nb.cells.append(nbformat.v4.new_code_cell("# YOUR CODE HERE"))
        nbformat.write(nb, str(tmp_path / "test.ipynb"))
        content = parser.parse(tmp_path)
        assert content.cells[0].status == CellStatus.TODO_CODE

    def test_not_implemented_error(
        self, parser: NotebookParser, tmp_path: Path
    ) -> None:
        nb = nbformat.v4.new_notebook()
        nb.cells.append(
            nbformat.v4.new_code_cell("def f():\n    raise NotImplementedError")
        )
        nbformat.write(nb, str(tmp_path / "test.ipynb"))
        content = parser.parse(tmp_path)
        assert content.cells[0].status == CellStatus.TODO_CODE

    def test_your_answer_here_markdown(
        self, parser: NotebookParser, tmp_path: Path
    ) -> None:
        nb = nbformat.v4.new_notebook()
        nb.cells.append(
            nbformat.v4.new_markdown_cell("Q: What?\n\n**Your answer here:**")
        )
        nbformat.write(nb, str(tmp_path / "test.ipynb"))
        content = parser.parse(tmp_path)
        assert content.cells[0].status == CellStatus.TODO_MARKDOWN

    def test_your_answer_here_uppercase(
        self, parser: NotebookParser, tmp_path: Path
    ) -> None:
        nb = nbformat.v4.new_notebook()
        nb.cells.append(nbformat.v4.new_markdown_cell("Q: What?\n\nYOUR ANSWER HERE"))
        nbformat.write(nb, str(tmp_path / "test.ipynb"))
        content = parser.parse(tmp_path)
        assert content.cells[0].status == CellStatus.TODO_MARKDOWN

    def test_answer_html_comment(self, parser: NotebookParser, tmp_path: Path) -> None:
        nb = nbformat.v4.new_notebook()
        nb.cells.append(nbformat.v4.new_markdown_cell("Q: Why?\n\n<!-- answer -->"))
        nbformat.write(nb, str(tmp_path / "test.ipynb"))
        content = parser.parse(tmp_path)
        assert content.cells[0].status == CellStatus.TODO_MARKDOWN

    def test_regular_code_not_todo(
        self, parser: NotebookParser, tmp_path: Path
    ) -> None:
        nb = nbformat.v4.new_notebook()
        nb.cells.append(nbformat.v4.new_code_cell("x = 42\nprint(x)"))
        nbformat.write(nb, str(tmp_path / "test.ipynb"))
        content = parser.parse(tmp_path)
        assert content.cells[0].status == CellStatus.ORIGINAL

    def test_regular_markdown_not_todo(
        self, parser: NotebookParser, tmp_path: Path
    ) -> None:
        nb = nbformat.v4.new_notebook()
        nb.cells.append(nbformat.v4.new_markdown_cell("# Just a heading"))
        nbformat.write(nb, str(tmp_path / "test.ipynb"))
        content = parser.parse(tmp_path)
        assert content.cells[0].status == CellStatus.ORIGINAL
