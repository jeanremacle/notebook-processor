"""Inventory scanner for package ingestion."""

from __future__ import annotations

import csv
import zipfile
from pathlib import Path

from charset_normalizer import from_path

from notebook_processor.models import Asset, AssetType, DataSchema

# File extension → AssetType mapping
_EXT_MAP: dict[str, AssetType] = {
    ".ipynb": AssetType.NOTEBOOK,
    # Data formats
    ".csv": AssetType.DATA,
    ".tsv": AssetType.DATA,
    ".parquet": AssetType.DATA,
    ".json": AssetType.DATA,
    # Image formats
    ".png": AssetType.IMAGE,
    ".jpg": AssetType.IMAGE,
    ".jpeg": AssetType.IMAGE,
    ".gif": AssetType.IMAGE,
    ".svg": AssetType.IMAGE,
    # Instruction formats
    ".md": AssetType.INSTRUCTIONS,
    ".txt": AssetType.INSTRUCTIONS,
}


class InventoryScanner:
    """Scans a raw assignment folder and identifies all files."""

    def scan(self, raw_dir: Path) -> list[Asset]:
        """Scan *raw_dir* and return an :class:`Asset` for every file."""
        if not raw_dir.is_dir():
            msg = f"Directory not found: {raw_dir}"
            raise FileNotFoundError(msg)

        assets: list[Asset] = []
        for file_path in sorted(raw_dir.rglob("*")):
            if not file_path.is_file():
                continue
            asset = self._classify(file_path, raw_dir)
            assets.append(asset)
        return assets

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _classify(self, file_path: Path, raw_dir: Path) -> Asset:
        """Build an :class:`Asset` for a single file."""
        ext = file_path.suffix.lower()
        asset_type = _EXT_MAP.get(ext, AssetType.SUPPLEMENT)
        rel_path = str(file_path.relative_to(raw_dir))
        size = file_path.stat().st_size

        schema_info: DataSchema | None = None
        contents: list[str] | None = None

        if ext == ".csv":
            schema_info = self._extract_csv_schema(file_path)
        elif ext == ".tsv":
            schema_info = self._extract_csv_schema(file_path, sep="\t")
        elif ext == ".zip":
            contents = self._list_zip_contents(file_path)

        return Asset(
            path=rel_path,
            type=asset_type,
            format=ext.lstrip(".") or "unknown",
            size_bytes=size,
            schema_info=schema_info,
            contents=contents,
        )

    def _extract_csv_schema(self, file_path: Path, sep: str = ",") -> DataSchema | None:
        """Extract schema info from a CSV/TSV using stdlib csv."""
        try:
            text = self._read_text(file_path)
            reader = csv.reader(text.splitlines(), delimiter=sep)
            rows = list(reader)
        except Exception:
            return None

        if len(rows) < 1:
            return None

        columns = rows[0]
        data_rows = rows[1:]
        row_count = len(data_rows)

        # Infer dtypes and count nulls per column
        dtypes: dict[str, str] = {}
        null_counts: dict[str, int] = {}
        for i, col in enumerate(columns):
            nulls = 0
            is_int = True
            is_float = True
            for row in data_rows:
                val = row[i] if i < len(row) else ""
                if val.strip() == "":
                    nulls += 1
                    continue
                if is_int:
                    try:
                        int(val)
                    except ValueError:
                        is_int = False
                if is_float and not is_int:
                    try:
                        float(val)
                    except ValueError:
                        is_float = False
            if is_int and nulls < row_count:
                dtypes[col] = "int64"
            elif is_float and nulls < row_count:
                dtypes[col] = "float64"
            else:
                dtypes[col] = "object"
            if nulls > 0:
                null_counts[col] = nulls

        # Build sample head/tail as dicts with coerced values
        def _row_to_dict(row: list[str]) -> dict[str, object]:
            d: dict[str, object] = {}
            for i, col in enumerate(columns):
                val = row[i] if i < len(row) else ""
                if val.strip() == "":
                    d[col] = None
                elif dtypes.get(col) == "int64":
                    d[col] = int(val)
                elif dtypes.get(col) == "float64":
                    d[col] = float(val)
                else:
                    d[col] = val
            return d

        head = [_row_to_dict(r) for r in data_rows[:3]]
        tail = [_row_to_dict(r) for r in data_rows[-2:]] if row_count >= 2 else list(head)

        return DataSchema(
            columns=columns,
            dtypes=dtypes,
            row_count=row_count,
            sample_head=head,
            sample_tail=tail,
            null_counts=null_counts,
        )

    @staticmethod
    def _read_text(file_path: Path) -> str:
        """Read a text file, auto-detecting encoding via charset_normalizer."""
        result = from_path(file_path)
        best = result.best()
        if best is None:
            return file_path.read_text(encoding="utf-8", errors="replace")
        return str(best)

    def _list_zip_contents(self, file_path: Path) -> list[str] | None:
        """List file names inside a ZIP archive without extracting."""
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                return zf.namelist()
        except (zipfile.BadZipFile, OSError):
            return None
