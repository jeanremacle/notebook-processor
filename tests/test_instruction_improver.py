"""Tests for InstructionImprover."""

from __future__ import annotations

from pathlib import Path

from notebook_processor.ingestion.instruction_improver import InstructionImprover
from notebook_processor.models import NotebookAnalysis


def _make_analysis() -> NotebookAnalysis:
    return NotebookAnalysis(
        total_cells=10,
        cell_type_counts={"code": 7, "markdown": 3},
        todo_markers=[],
        embedded_images_count=0,
        embedded_images_total_bytes=0,
    )


class TestInstructionImprover:
    def test_returns_empty_list(self) -> None:
        improver = InstructionImprover()
        result = improver.improve(_make_analysis())
        assert result == []

    def test_accepts_instructions_path(self, tmp_path: Path) -> None:
        md_path = tmp_path / "instructions.md"
        md_path.write_text("# Do the thing", encoding="utf-8")
        improver = InstructionImprover()
        result = improver.improve(_make_analysis(), instructions_path=md_path)
        assert result == []

    def test_accepts_rubric(self) -> None:
        improver = InstructionImprover()
        result = improver.improve(_make_analysis(), rubric="Grade on clarity")
        assert result == []

    def test_accepts_all_args(self, tmp_path: Path) -> None:
        md_path = tmp_path / "instructions.md"
        md_path.write_text("# Instructions", encoding="utf-8")
        improver = InstructionImprover()
        result = improver.improve(
            _make_analysis(),
            instructions_path=md_path,
            rubric="Grade on correctness",
        )
        assert result == []
