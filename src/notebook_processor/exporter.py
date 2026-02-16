"""Export notebooks to HTML via nbconvert."""

from __future__ import annotations

import logging
from pathlib import Path

import nbconvert
import nbformat

logger = logging.getLogger(__name__)


class NotebookExporter:
    """Exports executed notebooks to self-contained HTML."""

    def export_html(
        self,
        notebook_path: str | Path,
        output_path: str | Path | None = None,
    ) -> Path:
        """Export a notebook to self-contained HTML.

        Args:
            notebook_path: Path to the .ipynb file.
            output_path: Path for the HTML output. If None, uses the
                notebook path with .html extension.

        Returns:
            Path to the generated HTML file.
        """
        nb_path = Path(notebook_path)
        if not nb_path.exists():
            msg = f"Notebook not found: {nb_path}"
            raise FileNotFoundError(msg)

        if output_path is None:
            out_path = nb_path.with_suffix(".html")
        else:
            out_path = Path(output_path)

        out_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Exporting notebook to HTML: %s", nb_path)

        nb = nbformat.read(str(nb_path), as_version=4)  # type: ignore[no-untyped-call]
        exporter = nbconvert.HTMLExporter()  # type: ignore[no-untyped-call]
        body: str
        body, _ = exporter.from_notebook_node(nb)

        out_path.write_text(body, encoding="utf-8")

        logger.info("HTML exported: %s", out_path)
        return out_path
