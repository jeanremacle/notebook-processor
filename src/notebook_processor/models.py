"""Pydantic models for notebook processing."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class CellType(StrEnum):
    """Notebook cell types."""

    CODE = "code"
    MARKDOWN = "markdown"
    RAW = "raw"


class CellStatus(StrEnum):
    """Processing status of a notebook cell."""

    ORIGINAL = "original"
    TODO_CODE = "todo_code"
    TODO_MARKDOWN = "todo_markdown"
    COMPLETED = "completed"
    ADDED = "added"


class NotebookCell(BaseModel):
    """Represents a single notebook cell with processing metadata."""

    index: int
    cell_type: CellType
    source: str
    status: CellStatus = CellStatus.ORIGINAL
    original_source: str | None = None
    outputs: list[dict[str, object]] | None = None


class InstructionFile(BaseModel):
    """Parsed companion instruction file."""

    path: str
    content: str
    images: list[str] = []


class NotebookContent(BaseModel):
    """Complete parsed notebook with metadata."""

    path: str
    cells: list[NotebookCell]
    metadata: dict[str, object]
    instructions: InstructionFile | None = None
    kernel_spec: str | None = None


class PipelineState(BaseModel):
    """Tracks pipeline progress for resume capability."""

    input_path: str
    output_path: str
    done_path: str
    current_step: str
    completed_steps: list[str] = []
    errors: list[str] = []
