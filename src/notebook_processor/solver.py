"""Solver interface and implementations for completing notebook cells."""

from __future__ import annotations

from abc import ABC, abstractmethod

from notebook_processor.models import CellStatus, NotebookCell, NotebookContent


class NotebookSolver(ABC):
    """Interface for solving notebook cells."""

    @abstractmethod
    def solve_code_cell(self, cell: NotebookCell, context: NotebookContent) -> str:
        """Return completed source code for a TODO code cell."""
        ...

    @abstractmethod
    def solve_markdown_cell(self, cell: NotebookCell, context: NotebookContent) -> str:
        """Return answer text for a TODO markdown cell."""
        ...

    def solve(self, content: NotebookContent) -> NotebookContent:
        """Solve all TODO cells in a notebook.

        Args:
            content: Parsed notebook content with TODO cells detected.

        Returns:
            A new NotebookContent with TODO cells completed.
        """
        solved_cells: list[NotebookCell] = []
        for cell in content.cells:
            if cell.status == CellStatus.TODO_CODE:
                new_source = self.solve_code_cell(cell, content)
                solved_cells.append(
                    cell.model_copy(
                        update={
                            "source": new_source,
                            "status": CellStatus.COMPLETED,
                            "original_source": cell.source,
                        }
                    )
                )
            elif cell.status == CellStatus.TODO_MARKDOWN:
                new_source = self.solve_markdown_cell(cell, content)
                solved_cells.append(
                    cell.model_copy(
                        update={
                            "source": new_source,
                            "status": CellStatus.COMPLETED,
                            "original_source": cell.source,
                        }
                    )
                )
            else:
                solved_cells.append(cell)

        return content.model_copy(update={"cells": solved_cells})


class StubSolver(NotebookSolver):
    """Returns placeholder code/text for testing the pipeline."""

    def solve_code_cell(self, cell: NotebookCell, context: NotebookContent) -> str:
        """Return a placeholder pass statement."""
        return "# Stub solution\npass"

    def solve_markdown_cell(self, cell: NotebookCell, context: NotebookContent) -> str:
        """Return placeholder markdown text."""
        return "Stub answer: This is a placeholder response."


class ManualSolver(NotebookSolver):
    """Interactive solver that prompts for input on stdin."""

    def solve_code_cell(self, cell: NotebookCell, context: NotebookContent) -> str:
        """Print cell content and prompt for code input."""
        print(f"\n--- Code Cell {cell.index} ---")
        print(cell.source)
        print("---")
        print("Enter your solution (end with an empty line):")
        return self._read_multiline()

    def solve_markdown_cell(self, cell: NotebookCell, context: NotebookContent) -> str:
        """Print cell content and prompt for markdown input."""
        print(f"\n--- Markdown Cell {cell.index} ---")
        print(cell.source)
        print("---")
        print("Enter your answer (end with an empty line):")
        return self._read_multiline()

    def _read_multiline(self) -> str:
        """Read multi-line input until an empty line is entered."""
        lines: list[str] = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        return "\n".join(lines)
