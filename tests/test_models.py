"""Tests for notebook_processor.models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from notebook_processor.models import (
    CellStatus,
    CellType,
    InstructionFile,
    NotebookCell,
    NotebookContent,
    PipelineState,
)


class TestCellType:
    def test_values(self) -> None:
        assert CellType.CODE == "code"
        assert CellType.MARKDOWN == "markdown"
        assert CellType.RAW == "raw"


class TestCellStatus:
    def test_values(self) -> None:
        assert CellStatus.ORIGINAL == "original"
        assert CellStatus.TODO_CODE == "todo_code"
        assert CellStatus.TODO_MARKDOWN == "todo_markdown"
        assert CellStatus.COMPLETED == "completed"
        assert CellStatus.ADDED == "added"


class TestNotebookCell:
    def test_minimal(self) -> None:
        cell = NotebookCell(index=0, cell_type=CellType.CODE, source="x = 1")
        assert cell.index == 0
        assert cell.cell_type == CellType.CODE
        assert cell.source == "x = 1"
        assert cell.status == CellStatus.ORIGINAL
        assert cell.original_source is None
        assert cell.outputs is None

    def test_full(self) -> None:
        cell = NotebookCell(
            index=3,
            cell_type=CellType.MARKDOWN,
            source="# Hello",
            status=CellStatus.COMPLETED,
            original_source="# TODO",
            outputs=[{"output_type": "stream", "text": "hi"}],
        )
        assert cell.status == CellStatus.COMPLETED
        assert cell.original_source == "# TODO"
        assert cell.outputs is not None
        assert len(cell.outputs) == 1

    def test_invalid_cell_type(self) -> None:
        with pytest.raises(ValidationError):
            NotebookCell(index=0, cell_type="invalid", source="x = 1")  # type: ignore[arg-type]

    def test_serialization_roundtrip(self) -> None:
        cell = NotebookCell(
            index=0,
            cell_type=CellType.CODE,
            source="x = 1",
            status=CellStatus.TODO_CODE,
        )
        data = cell.model_dump()
        restored = NotebookCell.model_validate(data)
        assert restored == cell

    def test_json_roundtrip(self) -> None:
        cell = NotebookCell(index=0, cell_type=CellType.CODE, source="x = 1")
        json_str = cell.model_dump_json()
        restored = NotebookCell.model_validate_json(json_str)
        assert restored == cell


class TestInstructionFile:
    def test_minimal(self) -> None:
        inst = InstructionFile(path="instructions.md", content="Do this")
        assert inst.path == "instructions.md"
        assert inst.content == "Do this"
        assert inst.images == []

    def test_with_images(self) -> None:
        inst = InstructionFile(
            path="instructions.md",
            content="See image",
            images=["img1.png", "img2.png"],
        )
        assert len(inst.images) == 2


class TestNotebookContent:
    def test_minimal(self) -> None:
        content = NotebookContent(path="test.ipynb", cells=[], metadata={})
        assert content.path == "test.ipynb"
        assert content.cells == []
        assert content.instructions is None
        assert content.kernel_spec is None

    def test_with_cells(self) -> None:
        cells = [
            NotebookCell(index=0, cell_type=CellType.CODE, source="x = 1"),
            NotebookCell(
                index=1,
                cell_type=CellType.MARKDOWN,
                source="# Title",
                status=CellStatus.TODO_MARKDOWN,
            ),
        ]
        content = NotebookContent(
            path="test.ipynb",
            cells=cells,
            metadata={"kernelspec": {"name": "python3"}},
            kernel_spec="python3",
        )
        assert len(content.cells) == 2
        assert content.kernel_spec == "python3"

    def test_with_instructions(self) -> None:
        inst = InstructionFile(path="inst.md", content="Instructions")
        content = NotebookContent(
            path="test.ipynb",
            cells=[],
            metadata={},
            instructions=inst,
        )
        assert content.instructions is not None
        assert content.instructions.content == "Instructions"


class TestPipelineState:
    def test_minimal(self) -> None:
        state = PipelineState(
            input_path="input/",
            output_path="output/",
            done_path="done/",
            current_step="parse",
        )
        assert state.current_step == "parse"
        assert state.completed_steps == []
        assert state.errors == []

    def test_with_progress(self) -> None:
        state = PipelineState(
            input_path="input/",
            output_path="output/",
            done_path="done/",
            current_step="execute",
            completed_steps=["parse", "solve", "build"],
            errors=[],
        )
        assert len(state.completed_steps) == 3

    def test_with_errors(self) -> None:
        state = PipelineState(
            input_path="input/",
            output_path="output/",
            done_path="done/",
            current_step="execute",
            completed_steps=["parse", "solve", "build"],
            errors=["Cell 5 failed: ZeroDivisionError"],
        )
        assert len(state.errors) == 1

    def test_serialization_roundtrip(self) -> None:
        state = PipelineState(
            input_path="input/",
            output_path="output/",
            done_path="done/",
            current_step="build",
            completed_steps=["parse", "solve"],
        )
        data = state.model_dump()
        restored = PipelineState.model_validate(data)
        assert restored == state
