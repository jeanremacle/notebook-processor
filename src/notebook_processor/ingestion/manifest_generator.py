"""Manifest generator for package ingestion."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from notebook_processor.models import (
    Asset,
    AssetType,
    BenchmarkConfig,
    InstructionImprovement,
    LlmConfig,
    NotebookAnalysis,
    NotebookMetadata,
    PackageManifest,
    PackageMetadata,
)

logger = logging.getLogger(__name__)


class ManifestGenerator:
    """Assembles all ingestion outputs into a PackageManifest."""

    def generate(
        self,
        package_dir: Path,
        assets: list[Asset],
        analysis: NotebookAnalysis,
        improvements: list[InstructionImprovement] | None = None,
    ) -> PackageManifest:
        """Build and write the package manifest.

        Args:
            package_dir: Root directory of the notebook package.
            assets: All discovered assets from inventory scan.
            analysis: Notebook preprocessing results.
            improvements: Optional instruction improvements.

        Returns:
            The validated PackageManifest.
        """
        pkg_id = package_dir.name
        notebook_asset = next(
            (a for a in assets if a.type == AssetType.NOTEBOOK), None
        )
        original_filename = notebook_asset.path if notebook_asset else "notebook.ipynb"

        manifest = PackageManifest(
            package=PackageMetadata(
                id=pkg_id,
                name=pkg_id.replace("-", " ").replace("_", " ").title(),
                created_at=datetime.now(UTC).isoformat(),
                status="pending",
            ),
            notebook=NotebookMetadata(
                filename="notebook.ipynb",
                original_filename=original_filename,
                kernel=analysis.kernel_spec or "python3",
                analysis=analysis,
            ),
            assets=assets,
            instruction_improvements=improvements or [],
            llm_config=LlmConfig(),
            benchmark=BenchmarkConfig(),
        )

        # Write manifest.json
        manifest_path = package_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest.model_dump(), indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("Wrote manifest: %s", manifest_path)

        return manifest
