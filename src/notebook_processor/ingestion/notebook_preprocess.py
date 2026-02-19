"""Notebook preprocessor for package ingestion."""

from __future__ import annotations

import base64
import logging
import re
import shutil
from pathlib import Path
from typing import Any

import nbformat

from notebook_processor.ingestion.transformations import TransformationLogger
from notebook_processor.models import (
    CellType,
    DataQualityIssue,
    DataTransformation,
    ExtractedImage,
    NotebookAnalysis,
    TodoMarker,
)

logger = logging.getLogger(__name__)

# Base64 image pattern in markdown cells
_BASE64_MARKDOWN_RE = re.compile(
    r"!\[([^\]]*)\]\(data:image/(\w+);base64,([A-Za-z0-9+/=\s]+)\)",
)

# Default TODO marker patterns
DEFAULT_TODO_PATTERNS: list[str] = [
    # Standard patterns
    r"#\s*TODO",
    r"raise\s+NotImplementedError",
    r"#\s*YOUR\s+CODE\s+HERE",
    r"\*\*Your\s+answer\s+here\*\*",
    r"\*\*YOUR\s+ANSWER\s+HERE\*\*",
    # JHU patterns
    r"<--\s*YOUR\s+SYSTEM\s+PROMPT\s+GOES\s+HERE\s*-->",
    r"<--\s*YOUR\s+USER\s+PROMPT\s+GOES\s+HERE\s*-->",
    r"`<Enter\s+your\s+.*here>`",
    # HTML comment markers
    r"<!--\s*YOUR\s+ANSWER\s+HERE\s*-->",
]

# Import detection patterns
_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+(\w+)", re.MULTILINE)
_PIP_INSTALL_RE = re.compile(r"!pip\s+install\s+([\w\-]+)", re.MULTILINE)

# Known API service packages
_API_PACKAGES = frozenset(
    {"openai", "anthropic", "google", "cohere", "huggingface_hub", "replicate"}
)

# Hardcoded path patterns
_HARDCODED_PATH_RE = re.compile(
    r"""(?:["'])([^"']*(?:your_file|\.csv|\.tsv|\.json|\.xlsx|/path/to|\\path\\to)[^"']*)(?:["'])""",
    re.IGNORECASE,
)


class NotebookPreprocessor:
    """Preprocesses a notebook: extracts images, detects markers, scans deps."""

    def __init__(
        self,
        todo_patterns: list[str] | None = None,
    ) -> None:
        self._todo_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (todo_patterns or DEFAULT_TODO_PATTERNS)
        ]

    def preprocess(
        self,
        notebook_path: Path,
        package_dir: Path,
        xform_logger: TransformationLogger,
    ) -> NotebookAnalysis:
        """Run all preprocessing phases and return analysis results."""
        nb = nbformat.read(str(notebook_path), as_version=4)

        # Phase 3a — Extract embedded images
        images, nb = self._extract_images(nb, package_dir, xform_logger)

        # Phase 3b — Detect TODO markers
        markers = self._detect_markers(nb)

        # Phase 3c — Detect dependencies
        deps, api_deps = self._detect_dependencies(nb)

        # Phase 3d — Detect hardcoded paths
        hardcoded = self._detect_hardcoded_paths(nb)

        # Phase 3e — Save cleaned notebook + preserve original
        self._save_notebook(nb, notebook_path, package_dir)

        # Build analysis
        cell_types: dict[str, int] = {}
        for cell in nb.cells:
            ct = str(cell.cell_type)
            cell_types[ct] = cell_types.get(ct, 0) + 1

        total_bytes = sum(img.original_size_bytes for img in images)
        kernel = nb.metadata.get("kernelspec", {}).get("name")

        return NotebookAnalysis(
            total_cells=len(nb.cells),
            cell_type_counts=cell_types,
            todo_markers=markers,
            embedded_images_count=len(images),
            embedded_images_total_bytes=total_bytes,
            dependencies=deps,
            api_dependencies=api_deps,
            hardcoded_paths=hardcoded,
            kernel_spec=kernel,
        )

    # ------------------------------------------------------------------
    # Phase 3a — Image extraction
    # ------------------------------------------------------------------

    def _extract_images(
        self,
        nb: Any,
        package_dir: Path,
        xform_logger: TransformationLogger,
    ) -> tuple[list[ExtractedImage], Any]:
        """Extract base64 images from cell outputs and markdown."""
        images_dir = package_dir / "images"
        extracted: list[ExtractedImage] = []

        for i, cell in enumerate(nb.cells):
            # Check cell outputs for image/png data
            if cell.cell_type == "code" and hasattr(cell, "outputs"):
                for output in list(cell.outputs):
                    if hasattr(output, "data") and "image/png" in output.data:
                        b64_data = output.data["image/png"]
                        img = self._save_image(
                            b64_data, i, len(extracted), images_dir, package_dir
                        )
                        if img is not None:
                            extracted.append(img)
                            # Remove the image data from output
                            del output.data["image/png"]
                            if not output.data:
                                cell.outputs.remove(output)

            # Check markdown cells for inline base64 images
            if cell.cell_type == "markdown":
                cell.source, md_images = self._extract_markdown_images(
                    cell.source, i, len(extracted), images_dir, package_dir
                )
                extracted.extend(md_images)

        if extracted:
            xform_logger.log(
                DataTransformation(
                    original_path="notebook.ipynb",
                    issue=DataQualityIssue.ENCODING,
                    action="Extracted embedded images",
                    details=(
                        f"Extracted {len(extracted)} base64 image(s) "
                        f"totaling {sum(img.original_size_bytes for img in extracted)} bytes"
                    ),
                    records_affected=len(extracted),
                )
            )

        return extracted, nb

    def _save_image(
        self,
        b64_data: str,
        cell_index: int,
        image_index: int,
        images_dir: Path,
        package_dir: Path,
    ) -> ExtractedImage | None:
        """Decode and save a single base64 image."""
        try:
            cleaned = b64_data.replace("\n", "").replace(" ", "")
            data = base64.b64decode(cleaned)
        except Exception:
            return None

        images_dir.mkdir(parents=True, exist_ok=True)
        filename = f"sample_output_cell{cell_index}_{image_index}.png"
        img_path = images_dir / filename
        img_path.write_bytes(data)

        rel_path = str(img_path.relative_to(package_dir))
        logger.info("Extracted image: %s (%d bytes)", rel_path, len(data))

        return ExtractedImage(
            cell_index=cell_index,
            original_size_bytes=len(data),
            extracted_path=rel_path,
        )

    def _extract_markdown_images(
        self,
        source: str,
        cell_index: int,
        start_index: int,
        images_dir: Path,
        package_dir: Path,
    ) -> tuple[str, list[ExtractedImage]]:
        """Extract inline base64 images from markdown source."""
        extracted: list[ExtractedImage] = []
        idx = start_index

        def _replace(m: re.Match[str]) -> str:
            nonlocal idx
            alt = m.group(1) or "Sample Output"
            b64_data = m.group(3)
            img = self._save_image(b64_data, cell_index, idx, images_dir, package_dir)
            if img is not None:
                extracted.append(img)
                idx += 1
                return f"![{alt}]({img.extracted_path})"
            return m.group(0)

        new_source = _BASE64_MARKDOWN_RE.sub(_replace, source)
        return new_source, extracted

    # ------------------------------------------------------------------
    # Phase 3b — TODO marker detection
    # ------------------------------------------------------------------

    def _detect_markers(self, nb: Any) -> list[TodoMarker]:
        """Detect TODO markers in all cells."""
        markers: list[TodoMarker] = []
        for i, cell in enumerate(nb.cells):
            ct = CellType.CODE if cell.cell_type == "code" else CellType.MARKDOWN
            for pattern in self._todo_patterns:
                match = pattern.search(cell.source)
                if match:
                    var_name = self._extract_variable_name(cell.source, match)
                    markers.append(
                        TodoMarker(
                            cell_index=i,
                            cell_type=ct,
                            marker_pattern=pattern.pattern,
                            variable_name=var_name,
                            context=cell.source[:200],
                        )
                    )
                    break  # One marker per cell is enough
        return markers

    @staticmethod
    def _extract_variable_name(source: str, match: re.Match[str]) -> str | None:
        """Try to find the variable being assigned near the marker."""
        # Look for `variable_name = "..."` or `variable_name = '...'` near match
        line_start = source.rfind("\n", 0, match.start()) + 1
        line = source[line_start : match.end()]
        assign = re.match(r"(\w+)\s*=\s*", line)
        if assign:
            return assign.group(1)
        return None

    # ------------------------------------------------------------------
    # Phase 3c — Dependency detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_dependencies(nb: Any) -> tuple[list[str], list[str]]:
        """Scan code cells for imports and pip installs."""
        all_deps: set[str] = set()
        api_deps: set[str] = set()

        for cell in nb.cells:
            if cell.cell_type != "code":
                continue
            source = cell.source

            for m in _IMPORT_RE.finditer(source):
                pkg = m.group(1)
                all_deps.add(pkg)
                if pkg in _API_PACKAGES:
                    api_deps.add(pkg)

            for m in _PIP_INSTALL_RE.finditer(source):
                pkg = m.group(1)
                all_deps.add(pkg)
                if pkg in _API_PACKAGES:
                    api_deps.add(pkg)

        # Filter out stdlib modules
        stdlib = {"os", "sys", "re", "json", "csv", "math", "datetime", "pathlib",
                  "collections", "itertools", "functools", "typing", "abc",
                  "io", "logging", "time", "copy", "string", "textwrap",
                  "warnings", "dataclasses", "enum", "random", "hashlib",
                  "base64", "unittest", "pprint", "shutil", "tempfile",
                  "glob", "subprocess", "argparse", "configparser"}
        filtered = sorted(all_deps - stdlib)

        return filtered, sorted(api_deps)

    # ------------------------------------------------------------------
    # Phase 3d — Hardcoded path detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_hardcoded_paths(nb: Any) -> list[str]:
        """Scan code cells for hardcoded file paths."""
        paths: list[str] = []
        for cell in nb.cells:
            if cell.cell_type != "code":
                continue
            for m in _HARDCODED_PATH_RE.finditer(cell.source):
                paths.append(m.group(1))
        return paths

    # ------------------------------------------------------------------
    # Phase 3e — Save cleaned notebook
    # ------------------------------------------------------------------

    @staticmethod
    def _save_notebook(nb: Any, original_path: Path, package_dir: Path) -> None:
        """Save cleaned notebook and preserve original."""
        cleaned_path = package_dir / "notebook.ipynb"
        orig_path = package_dir / "notebook.ipynb.orig"

        # Preserve original
        if original_path.exists():
            shutil.copy2(original_path, orig_path)

        # Write cleaned
        nbformat.write(nb, str(cleaned_path))
        logger.info("Saved cleaned notebook: %s", cleaned_path)
