"""Package ingestor — orchestrates the full ingestion pipeline."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from notebook_processor.ingestion.data_repair import DataRepairer
from notebook_processor.ingestion.instruction_improver import InstructionImprover
from notebook_processor.ingestion.inventory import InventoryScanner
from notebook_processor.ingestion.manifest_generator import ManifestGenerator
from notebook_processor.ingestion.notebook_preprocess import NotebookPreprocessor
from notebook_processor.ingestion.transformations import TransformationLogger
from notebook_processor.models import AssetType, PackageManifest

logger = logging.getLogger(__name__)


class PackageIngestor:
    """Orchestrates the full package ingestion pipeline.

    Pipeline phases:
        1. Inventory — scan and classify all files
        2. Data repair — fix encoding and line endings
        3. Notebook preprocessing — extract images, detect markers
        4. Instruction improvement — (stub) improve instructions
        5. Manifest generation — assemble and write manifest.json
    """

    def __init__(self) -> None:
        self._scanner = InventoryScanner()
        self._repairer = DataRepairer()
        self._preprocessor = NotebookPreprocessor()
        self._improver = InstructionImprover()
        self._manifest_gen = ManifestGenerator()

    def ingest(self, raw_dir: Path, target_dir: Path) -> PackageManifest:
        """Run the full ingestion pipeline.

        Args:
            raw_dir: Source directory containing raw assignment files.
            target_dir: Destination directory for the normalized package.

        Returns:
            The validated PackageManifest.
        """
        if not raw_dir.is_dir():
            msg = f"Source directory not found: {raw_dir}"
            raise FileNotFoundError(msg)

        target_dir.mkdir(parents=True, exist_ok=True)
        xform_logger = TransformationLogger()

        logger.info("Starting ingestion: %s → %s", raw_dir, target_dir)

        # Phase 1 — Inventory
        logger.info("Phase 1: Scanning inventory")
        assets = self._scanner.scan(raw_dir)
        logger.info("Found %d assets", len(assets))

        # Copy all files into target directory
        self._copy_files(raw_dir, target_dir, assets)

        # Phase 2 — Data repair
        logger.info("Phase 2: Repairing data files")
        repaired_assets = []
        for asset in assets:
            if asset.type == AssetType.DATA:
                asset = self._repairer.repair(asset, target_dir, xform_logger)
            repaired_assets.append(asset)

        # Phase 3 — Notebook preprocessing
        logger.info("Phase 3: Preprocessing notebook")
        notebook_asset = next(
            (a for a in repaired_assets if a.type == AssetType.NOTEBOOK), None
        )
        if notebook_asset is None:
            msg = "No notebook found in source directory"
            raise FileNotFoundError(msg)

        notebook_path = target_dir / notebook_asset.path
        analysis = self._preprocessor.preprocess(
            notebook_path, target_dir, xform_logger
        )

        # Phase 4 — Instruction improvement
        logger.info("Phase 4: Improving instructions")
        instructions_asset = next(
            (a for a in repaired_assets if a.type == AssetType.INSTRUCTIONS), None
        )
        instructions_path = (
            target_dir / instructions_asset.path if instructions_asset else None
        )
        improvements = self._improver.improve(analysis, instructions_path)

        # Phase 5 — Manifest generation
        logger.info("Phase 5: Generating manifest")
        manifest = self._manifest_gen.generate(
            target_dir, repaired_assets, analysis, improvements
        )

        # Save transformations log
        xform_logger.save(target_dir / "transformations.log")
        logger.info("Ingestion complete: %s", xform_logger.get_summary())

        return manifest

    def ingest_project(
        self,
        layout: object,
        *,
        force: bool = False,
    ) -> PackageManifest:
        """Convention-aware ingestion using a :class:`ProjectLayout`.

        Moves loose files in the project root into ``input/``, then runs
        the full ingestion pipeline writing results to ``ingested/``.

        Args:
            layout: A ``ProjectLayout`` instance.
            force: If ``True``, re-ingest even if ``ingested/manifest.json`` exists,
                   and allow archiving when ``input/`` is already populated.

        Returns:
            The validated PackageManifest.
        """
        from notebook_processor.project_layout import ProjectLayout

        if not isinstance(layout, ProjectLayout):
            msg = "layout must be a ProjectLayout instance"
            raise TypeError(msg)

        layout.ensure_dirs()
        self._archive_originals(layout, force=force)

        manifest_path = layout.ingested_dir / "manifest.json"
        if manifest_path.exists() and not force:
            import json

            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return PackageManifest.model_validate(data)

        if force and layout.ingested_dir.exists():
            shutil.rmtree(layout.ingested_dir)
            layout.ingested_dir.mkdir()

        return self.ingest(layout.input_dir, layout.ingested_dir)

    @staticmethod
    def _archive_originals(
        layout: object,
        *,
        force: bool = False,
    ) -> None:
        """Move loose files from the project root into ``input/``.

        Args:
            layout: A ``ProjectLayout`` instance.
            force: If ``True``, allow archiving even when ``input/`` is populated.
        """
        from notebook_processor.project_layout import ProjectLayout

        if not isinstance(layout, ProjectLayout):
            msg = "layout must be a ProjectLayout instance"
            raise TypeError(msg)

        if not layout.has_loose_files():
            return

        if layout.input_already_populated() and not force:
            msg = (
                f"input/ already contains files and loose files exist in "
                f"{layout.root}. Use force=True to overwrite."
            )
            raise FileExistsError(msg)

        layout.input_dir.mkdir(parents=True, exist_ok=True)
        for child in layout.root.iterdir():
            if child.name not in ProjectLayout._SUBDIRS:
                shutil.move(str(child), str(layout.input_dir / child.name))

    @staticmethod
    def _copy_files(
        raw_dir: Path,
        target_dir: Path,
        assets: list,  # type: ignore[type-arg]
    ) -> None:
        """Copy all source files into the target package directory."""
        for asset in assets:
            src = raw_dir / asset.path
            dst = target_dir / asset.path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
