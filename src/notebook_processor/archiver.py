"""Archive input files to done/ for preservation."""

from __future__ import annotations

import filecmp
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class NotebookArchiver:
    """Copies input files to a done directory for preservation."""

    def archive(self, input_dir: str | Path, done_dir: str | Path) -> None:
        """Copy all files from input_dir to done_dir.

        Preserves directory structure. Skips files that are identical
        to existing files in done_dir (idempotent).

        Args:
            input_dir: Source directory to archive.
            done_dir: Destination directory.
        """
        src = Path(input_dir)
        dst = Path(done_dir)

        if not src.exists():
            msg = f"Input directory not found: {src}"
            raise FileNotFoundError(msg)

        dst.mkdir(parents=True, exist_ok=True)

        for src_file in src.rglob("*"):
            if not src_file.is_file():
                continue

            relative = src_file.relative_to(src)
            dst_file = dst / relative

            if dst_file.exists() and filecmp.cmp(
                str(src_file), str(dst_file), shallow=False
            ):
                logger.debug("Skipping identical file: %s", relative)
                continue

            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_file), str(dst_file))
            logger.info("Archived: %s", relative)
