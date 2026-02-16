"""Parse Jupyter notebooks and detect TODO cells."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import nbformat

from notebook_processor.models import (
    CellStatus,
    CellType,
    InstructionFile,
    NotebookCell,
    NotebookContent,
)

# Patterns that indicate a code cell needs completion
_CODE_TODO_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"#\s*TODO", re.IGNORECASE),
    re.compile(r"#\s*YOUR\s+CODE\s+HERE", re.IGNORECASE),
    re.compile(r"raise\s+NotImplementedError"),
]

# Patterns that indicate a markdown cell needs an answer
_MARKDOWN_TODO_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\*\*Your\s+answer\s+here\b", re.IGNORECASE),
    re.compile(r"YOUR\s+ANSWER\s+HERE"),
    re.compile(r"<!--\s*answer\s*-->", re.IGNORECASE),
]


def _detect_code_todo(source: str) -> bool:
    """Check if a code cell contains TODO markers."""
    return any(p.search(source) for p in _CODE_TODO_PATTERNS)


def _detect_markdown_todo(source: str) -> bool:
    """Check if a markdown cell contains answer placeholders."""
    return any(p.search(source) for p in _MARKDOWN_TODO_PATTERNS)


def _is_empty_code_cell(source: str) -> bool:
    """Check if a code cell is effectively empty."""
    stripped = source.strip()
    return stripped == "" or stripped == "pass"


class NotebookParser:
    """Reads .ipynb files and extracts cells with TODO detection."""

    def parse(self, input_dir: str | Path) -> NotebookContent:
        """Parse a notebook from an input directory.

        Args:
            input_dir: Directory containing a .ipynb file, optional
                instructions.md, and optional images/ subdirectory.

        Returns:
            Parsed notebook content with TODO cells detected.

        Raises:
            FileNotFoundError: If no .ipynb file is found.
        """
        input_path = Path(input_dir)
        notebook_path = self._find_notebook(input_path)
        nb = nbformat.read(str(notebook_path), as_version=4)  # type: ignore[no-untyped-call]

        cells = self._extract_cells(nb)
        metadata = dict(nb.metadata)
        kernel_spec = self._extract_kernel_spec(nb)
        instructions = self._load_instructions(input_path)

        return NotebookContent(
            path=str(notebook_path),
            cells=cells,
            metadata=metadata,
            instructions=instructions,
            kernel_spec=kernel_spec,
        )

    def _find_notebook(self, input_dir: Path) -> Path:
        """Find the first .ipynb file in the input directory."""
        notebooks = list(input_dir.glob("*.ipynb"))
        if not notebooks:
            msg = f"No .ipynb file found in {input_dir}"
            raise FileNotFoundError(msg)
        return notebooks[0]

    def _extract_cells(
        self,
        nb: Any,
    ) -> list[NotebookCell]:
        """Extract cells from a notebook with TODO detection."""
        cells: list[NotebookCell] = []
        for i, cell in enumerate(nb.cells):
            source: str = cell.source
            cell_type = CellType(cell.cell_type)
            status = self._classify_cell(cell_type, source)

            outputs: list[dict[str, object]] | None = None
            if cell_type == CellType.CODE and hasattr(cell, "outputs"):
                outputs = [dict(o) for o in cell.outputs]

            cells.append(
                NotebookCell(
                    index=i,
                    cell_type=cell_type,
                    source=source,
                    status=status,
                    outputs=outputs,
                )
            )
        return cells

    def _classify_cell(self, cell_type: CellType, source: str) -> CellStatus:
        """Determine the status of a cell based on its content."""
        if cell_type == CellType.CODE and (
            _detect_code_todo(source) or _is_empty_code_cell(source)
        ):
            return CellStatus.TODO_CODE
        if cell_type == CellType.MARKDOWN and _detect_markdown_todo(source):
            return CellStatus.TODO_MARKDOWN
        return CellStatus.ORIGINAL

    def _extract_kernel_spec(
        self,
        nb: Any,
    ) -> str | None:
        """Extract kernel spec name from notebook metadata."""
        ks = nb.metadata.get("kernelspec", {})
        result: str | None = ks.get("name")
        return result

    def _load_instructions(self, input_dir: Path) -> InstructionFile | None:
        """Load companion instructions.md if present."""
        instructions_path = input_dir / "instructions.md"
        if not instructions_path.exists():
            return None

        content = instructions_path.read_text(encoding="utf-8")
        images = self._find_images(input_dir)

        return InstructionFile(
            path=str(instructions_path),
            content=content,
            images=images,
        )

    def _find_images(self, input_dir: Path) -> list[str]:
        """Find image files in the images/ subdirectory."""
        images_dir = input_dir / "images"
        if not images_dir.exists():
            return []
        extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".bmp"}
        return sorted(
            str(p) for p in images_dir.iterdir() if p.suffix.lower() in extensions
        )
