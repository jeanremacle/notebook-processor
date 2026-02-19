"""Data repair for package ingestion — encoding and line-ending normalization."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from charset_normalizer import from_path

from notebook_processor.ingestion.transformations import TransformationLogger
from notebook_processor.models import Asset, DataQualityIssue, DataTransformation

logger = logging.getLogger(__name__)


class DataRepairer:
    """Detects and repairs encoding / line-ending issues in data files."""

    def repair(
        self,
        asset: Asset,
        package_dir: Path,
        xform_logger: TransformationLogger,
    ) -> Asset:
        """Repair a single data asset in-place, logging every change.

        Returns an updated copy of *asset* with transformations appended.
        """
        file_path = package_dir / asset.path
        if not file_path.is_file():
            return asset

        transformations: list[DataTransformation] = list(asset.transformations)

        # --- Encoding detection & conversion ---
        encoding_xform = self._fix_encoding(file_path, asset.path, package_dir)
        if encoding_xform is not None:
            transformations.append(encoding_xform)
            xform_logger.log(encoding_xform)

        # --- Line-ending normalization (must run after encoding fix) ---
        le_xform = self._fix_line_endings(file_path, asset.path)
        if le_xform is not None:
            transformations.append(le_xform)
            xform_logger.log(le_xform)

        return asset.model_copy(update={"transformations": transformations})

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fix_encoding(
        self,
        file_path: Path,
        rel_path: str,
        package_dir: Path,
    ) -> DataTransformation | None:
        """Detect non-UTF-8 encoding and convert to UTF-8."""
        result = from_path(file_path)
        best = result.best()
        if best is None:
            return None

        detected = best.encoding.lower()

        # Already UTF-8 — nothing to do
        if detected in ("utf-8", "ascii"):
            return None

        # Preserve original
        orig_path = file_path.with_suffix(file_path.suffix + ".orig")
        shutil.copy2(file_path, orig_path)

        # Read with detected encoding, write as UTF-8
        raw = file_path.read_bytes()
        text = raw.decode(detected, errors="replace")
        file_path.write_text(text, encoding="utf-8")

        # Count character substitutions for logging
        char_subs = self._count_substitutions(raw, detected)
        details = f"Converted {detected} → UTF-8"
        if char_subs:
            details += ": " + ", ".join(
                f"U+{ord(c):04X} ({c!r}) ×{n}" for c, n in char_subs.items()
            )

        backup_rel = str(orig_path.relative_to(package_dir))

        logger.info("Encoding fix: %s (%s → UTF-8)", rel_path, detected)

        return DataTransformation(
            original_path=rel_path,
            issue=DataQualityIssue.ENCODING,
            action=f"Converted from {detected} to UTF-8",
            details=details,
            records_affected=text.count("\n"),
            backup_path=backup_rel,
        )

    @staticmethod
    def _count_substitutions(raw: bytes, encoding: str) -> dict[str, int]:
        """Count non-ASCII characters that differ between encodings."""
        counts: dict[str, int] = {}
        for byte in raw:
            if byte >= 0x80:
                try:
                    char = bytes([byte]).decode(encoding)
                    counts[char] = counts.get(char, 0) + 1
                except (UnicodeDecodeError, ValueError):
                    pass
        return counts

    @staticmethod
    def _fix_line_endings(
        file_path: Path,
        rel_path: str,
    ) -> DataTransformation | None:
        """Normalize \\r\\n to \\n."""
        raw = file_path.read_bytes()
        crlf_count = raw.count(b"\r\n")
        if crlf_count == 0:
            return None

        normalized = raw.replace(b"\r\n", b"\n")
        file_path.write_bytes(normalized)

        logger.info("Line endings: %s (%d CRLF → LF)", rel_path, crlf_count)

        return DataTransformation(
            original_path=rel_path,
            issue=DataQualityIssue.LINE_ENDINGS,
            action="Normalized CRLF to LF",
            details=f"Replaced {crlf_count} CRLF line endings with LF",
            records_affected=crlf_count,
        )
