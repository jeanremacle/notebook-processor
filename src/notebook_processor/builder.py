"""Reconstruct .ipynb notebooks from modified cells."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import nbformat

from notebook_processor.models import CellStatus, CellType, NotebookContent


class NotebookBuilder:
    """Reconstructs valid .ipynb files from NotebookContent."""

    def build(self, content: NotebookContent, output_path: str | Path) -> Path:
        """Build a .ipynb file from processed notebook content.

        Args:
            content: Notebook content with completed cells.
            output_path: Path for the output .ipynb file.

        Returns:
            Path to the written notebook file.
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        nb = self._create_notebook(content)
        nbformat.write(nb, str(output))
        return output

    def _create_notebook(self, content: NotebookContent) -> Any:
        """Create an nbformat notebook node from content."""
        nb = nbformat.v4.new_notebook()
        nb.metadata = nbformat.from_dict(content.metadata)

        for cell in content.cells:
            nb_cell = self._create_cell(cell.cell_type, cell.source)
            # Clear outputs for completed cells (executor will repopulate)
            if cell.status == CellStatus.COMPLETED and cell.cell_type == CellType.CODE:
                nb_cell.outputs = []
            elif cell.cell_type == CellType.CODE and cell.outputs:
                nb_cell.outputs = [nbformat.from_dict(o) for o in cell.outputs]
            nb.cells.append(nb_cell)

        return nb

    def _create_cell(self, cell_type: CellType, source: str) -> Any:
        """Create an nbformat cell node."""
        if cell_type == CellType.CODE:
            return nbformat.v4.new_code_cell(source)
        if cell_type == CellType.MARKDOWN:
            return nbformat.v4.new_markdown_cell(source)
        return nbformat.v4.new_raw_cell(source)
