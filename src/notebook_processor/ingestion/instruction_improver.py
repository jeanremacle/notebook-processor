"""Instruction improver for package ingestion (stub for MVP)."""

from __future__ import annotations

import logging
from pathlib import Path

from notebook_processor.models import InstructionImprovement, NotebookAnalysis

logger = logging.getLogger(__name__)


class InstructionImprover:
    """Analyzes and improves assignment instructions.

    MVP: returns an empty list. The full implementation will use an LLM
    (via the Solver interface) to:
    - Merge notebook markdown with external instruction files
    - Identify vague or ambiguous instructions
    - Propose sub-step decomposition
    - Map rubric criteria to measurable objectives
    """

    def improve(
        self,
        analysis: NotebookAnalysis,
        instructions_path: Path | None = None,
        rubric: str | None = None,
    ) -> list[InstructionImprovement]:
        """Analyze instructions and suggest improvements.

        Args:
            analysis: Notebook preprocessing results.
            instructions_path: Path to external instructions file (.md/.txt).
            rubric: Optional rubric text for criteria mapping.

        Returns:
            List of instruction improvements (empty in MVP stub).
        """
        logger.debug(
            "InstructionImprover.improve() called (stub): "
            "analysis=%d cells, instructions=%s, rubric=%s",
            analysis.total_cells,
            instructions_path,
            "provided" if rubric else "none",
        )
        return []
