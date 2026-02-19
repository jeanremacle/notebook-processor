"""Unified project folder layout — single source of truth for path resolution."""

from __future__ import annotations

import re
from pathlib import Path


class ProjectLayout:
    """Resolve and manage the canonical project directory structure.

    The layout is::

        root/
        ├── input/       ← originals moved here
        ├── ingested/    ← normalized package
        └── output/
            ├── run-001/ ← auto-sequential
            └── custom/  ← user-provided name

    If *path* is named ``"input"``, the root is its parent; otherwise *path*
    itself is treated as the root.
    """

    _SUBDIRS = {"input", "ingested", "output"}
    _RUN_PATTERN = re.compile(r"^run-(\d{3})$")

    def __init__(self, path: str | Path) -> None:
        p = Path(path).resolve()
        if p.name == "input":
            self._root = p.parent
        else:
            self._root = p

    # -- path properties ---------------------------------------------------

    @property
    def root(self) -> Path:
        return self._root

    @property
    def input_dir(self) -> Path:
        return self._root / "input"

    @property
    def ingested_dir(self) -> Path:
        return self._root / "ingested"

    @property
    def output_dir(self) -> Path:
        return self._root / "output"

    # -- run directory -----------------------------------------------------

    def run_dir(self, name: str | None = None) -> Path:
        """Return the output sub-directory for a specific run.

        If *name* is ``None``, auto-generates the next sequential
        ``run-NNN`` name.
        """
        if name is not None:
            return self.output_dir / name
        return self.output_dir / self._next_run_name()

    def _next_run_name(self) -> str:
        """Scan ``output/`` for ``run-\\d{3}`` dirs, return next name."""
        max_n = 0
        if self.output_dir.is_dir():
            for child in self.output_dir.iterdir():
                if child.is_dir():
                    m = self._RUN_PATTERN.match(child.name)
                    if m:
                        max_n = max(max_n, int(m.group(1)))
        return f"run-{max_n + 1:03d}"

    # -- loose-file detection ----------------------------------------------

    def has_loose_files(self) -> bool:
        """Return ``True`` if root contains files/dirs outside the canonical subdirs."""
        if not self._root.is_dir():
            return False
        for child in self._root.iterdir():
            if child.name not in self._SUBDIRS:
                return True
        return False

    def input_already_populated(self) -> bool:
        """Return ``True`` if ``input/`` has any content."""
        if not self.input_dir.is_dir():
            return False
        return any(self.input_dir.iterdir())

    # -- directory creation ------------------------------------------------

    def ensure_dirs(self) -> None:
        """Create all three canonical subdirectories if absent."""
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.ingested_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
