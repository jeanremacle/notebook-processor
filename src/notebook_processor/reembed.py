"""Re-embed original images into a completed notebook for validation."""

from __future__ import annotations

import logging
from pathlib import Path

import nbformat

logger = logging.getLogger(__name__)


def reembed_images(
    original_notebook: str | Path,
    completed_notebook: str | Path,
    output_path: str | Path,
) -> Path:
    """Inject original cell outputs back into the completed notebook.

    The original notebook (from ``input/``) has all base64 images intact.
    The completed notebook (from ``output/{run}/``) has the answers but
    images were stripped during ingestion.  This function merges them.

    Args:
        original_notebook: Path to the original notebook with images.
        completed_notebook: Path to the completed notebook.
        output_path: Where to write the merged notebook.

    Returns:
        Path to the merged notebook.
    """
    orig_path = Path(original_notebook)
    comp_path = Path(completed_notebook)
    out_path = Path(output_path)

    orig_nb = nbformat.read(str(orig_path), as_version=4)
    comp_nb = nbformat.read(str(comp_path), as_version=4)

    # Build a map of cell_id -> outputs from the original notebook
    orig_outputs: dict[str, list[object]] = {}
    for cell in orig_nb.cells:
        cell_id = cell.get("id", "")
        if cell.cell_type == "code" and cell_id:
            outputs = cell.get("outputs", [])
            if outputs:
                orig_outputs[cell_id] = outputs

    restored = 0
    for cell in comp_nb.cells:
        cell_id = cell.get("id", "")
        if cell.cell_type == "code" and cell_id and cell_id in orig_outputs:
            existing = cell.get("outputs", [])
            # Only re-embed if the completed cell has no image outputs
            has_images = any(
                "image/png" in (out.get("data", {}) if isinstance(out, dict) else {})
                for out in existing
            )
            if not has_images:
                cell["outputs"] = orig_outputs[cell_id]
                restored += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(comp_nb, str(out_path))

    logger.info("Re-embedded outputs from %d cells into %s", restored, out_path)
    return out_path
