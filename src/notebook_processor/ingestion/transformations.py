"""Transformation logger for package ingestion."""

from __future__ import annotations

from pathlib import Path

from notebook_processor.models import DataTransformation


class TransformationLogger:
    """Append-only log of data transformations applied during ingestion."""

    def __init__(self) -> None:
        self._entries: list[DataTransformation] = []

    @property
    def entries(self) -> list[DataTransformation]:
        """Return a copy of all logged transformations."""
        return list(self._entries)

    def log(self, transformation: DataTransformation) -> None:
        """Append a transformation record."""
        self._entries.append(transformation)

    def save(self, path: Path) -> None:
        """Write transformations.log as human-readable text."""
        lines: list[str] = []
        for i, t in enumerate(self._entries, start=1):
            lines.append(f"[{i}] {t.issue.upper()} — {t.action}")
            lines.append(f"    File: {t.original_path}")
            lines.append(f"    Details: {t.details}")
            if t.records_affected:
                lines.append(f"    Records affected: {t.records_affected}")
            if t.confidence < 1.0:
                lines.append(f"    Confidence: {t.confidence:.0%}")
            if t.backup_path:
                lines.append(f"    Backup: {t.backup_path}")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    def get_summary(self) -> str:
        """Return a one-line summary of all transformations."""
        if not self._entries:
            return "No transformations applied."
        issues: dict[str, int] = {}
        for t in self._entries:
            issues[t.issue] = issues.get(t.issue, 0) + 1
        parts = [f"{count} {issue}" for issue, count in issues.items()]
        return f"{len(self._entries)} transformation(s): {', '.join(parts)}"
