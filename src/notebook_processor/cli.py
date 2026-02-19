"""CLI for notebook-processor using click."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler

from notebook_processor.executor import NotebookExecutor
from notebook_processor.exporter import NotebookExporter
from notebook_processor.ingestion.ingestor import PackageIngestor
from notebook_processor.parser import NotebookParser
from notebook_processor.pipeline import ProcessingPipeline
from notebook_processor.project_layout import ProjectLayout
from notebook_processor.reembed import reembed_images
from notebook_processor.solver import StubSolver

console = Console()


def _setup_logging(verbose: bool) -> None:
    """Configure logging with rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_time=False)],
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
def main(verbose: bool) -> None:
    """Notebook Processor — automated notebook pipeline."""
    _setup_logging(verbose)


# ---------------------------------------------------------------------------
# Project-aware commands (unified folder convention)
# ---------------------------------------------------------------------------


@main.command()
@click.argument("folder", type=click.Path(exists=True))
@click.option("--force", is_flag=True, help="Re-ingest even if cached.")
def ingest(folder: str, force: bool) -> None:
    """Ingest a raw assignment folder into a normalized package.

    FOLDER is the project root (or its input/ subdirectory).
    Moves originals into input/, writes ingestion output to ingested/.
    """
    layout = ProjectLayout(folder)
    ingestor = PackageIngestor()

    console.print(f"[bold]Ingesting:[/bold] {layout.root}")
    manifest = ingestor.ingest_project(layout, force=force)

    analysis = manifest.notebook.analysis
    console.print(f"[green]Assets:[/green] {len(manifest.assets)} files")
    if analysis:
        console.print(f"[green]TODO markers:[/green] {len(analysis.todo_markers)}")
        console.print(
            f"[green]Images extracted:[/green] {analysis.embedded_images_count}"
        )
        console.print(
            f"[green]Dependencies:[/green] "
            f"{', '.join(analysis.dependencies) or 'none'}"
        )
    console.print(f"[green]Manifest:[/green] {layout.ingested_dir / 'manifest.json'}")


@main.command()
@click.argument("folder", type=click.Path(exists=True))
@click.option("--name", default=None, help="Custom run name (default: auto-sequential).")
def process(folder: str, name: str | None) -> None:
    """Run the full processing pipeline on an ingested package.

    FOLDER is the project root (or its input/ subdirectory).
    Reads from ingested/, writes output to output/{name}.
    """
    layout = ProjectLayout(folder)
    run_dir = layout.run_dir(name)

    solver = StubSolver()
    pipeline = ProcessingPipeline()

    console.print(f"[bold]Processing:[/bold] {layout.ingested_dir} → {run_dir}")
    state = pipeline.run(layout.ingested_dir, run_dir, done_dir=None, solver=solver)

    console.print(
        f"[green]Completed steps:[/green] {', '.join(state.completed_steps)}"
    )
    if state.errors:
        console.print(f"[red]Errors:[/red] {state.errors}")


@main.command()
@click.argument("folder", type=click.Path(exists=True))
@click.option("--name", default=None, help="Custom run name (default: auto-sequential).")
@click.option("--force", is_flag=True, help="Re-ingest even if cached.")
def run(folder: str, name: str | None, force: bool) -> None:
    """Ingest and then process in one step.

    FOLDER is the project root (or its input/ subdirectory).
    """
    layout = ProjectLayout(folder)
    ingestor = PackageIngestor()
    pipeline = ProcessingPipeline()
    solver = StubSolver()

    console.print(f"[bold]Running:[/bold] {layout.root}")

    # Ingest
    manifest = ingestor.ingest_project(layout, force=force)
    analysis = manifest.notebook.analysis
    console.print(f"[green]Ingested:[/green] {len(manifest.assets)} assets")
    if analysis:
        console.print(f"[green]TODO markers:[/green] {len(analysis.todo_markers)}")

    # Process
    run_dir = layout.run_dir(name)
    state = pipeline.run(layout.ingested_dir, run_dir, done_dir=None, solver=solver)

    console.print(
        f"[green]Completed steps:[/green] {', '.join(state.completed_steps)}"
    )
    console.print(f"[green]Output:[/green] {run_dir}")
    if state.errors:
        console.print(f"[red]Errors:[/red] {state.errors}")


@main.command()
@click.argument("folder", type=click.Path(exists=True))
@click.option(
    "--name", default=None, help="Run name to validate (default: latest run)."
)
def validate(folder: str, name: str | None) -> None:
    """Re-embed original images and export validated HTML.

    FOLDER is the project root (or its input/ subdirectory).
    Reads the completed notebook from output/{name}/, re-embeds images
    from the original notebook in input/, and exports to HTML.
    """
    layout = ProjectLayout(folder)

    # Find the run directory
    if name is not None:
        run_dir = layout.run_dir(name)
    else:
        # Find the latest run directory
        run_dir = _find_latest_run(layout)

    if not run_dir.is_dir():
        console.print(f"[red]Run directory not found:[/red] {run_dir}")
        raise SystemExit(1)

    # Find the completed notebook in the run directory
    completed_nb = _find_notebook(run_dir, suffix="_completed.ipynb")
    if completed_nb is None:
        console.print(f"[red]No completed notebook found in:[/red] {run_dir}")
        raise SystemExit(1)

    # Find the original notebook in input/
    original_nb = _find_notebook(layout.input_dir)
    if original_nb is None:
        console.print(f"[red]No original notebook found in:[/red] {layout.input_dir}")
        raise SystemExit(1)

    console.print(f"[bold]Validating:[/bold] {completed_nb.name}")

    # Re-embed images
    validated_nb = run_dir / "validated.ipynb"
    reembed_images(original_nb, completed_nb, validated_nb)

    # Export to HTML
    exporter = NotebookExporter()
    html_path = run_dir / "validated.html"
    exporter.export_html(validated_nb, html_path)

    console.print(f"[green]Validated notebook:[/green] {validated_nb}")
    console.print(f"[green]HTML export:[/green] {html_path}")


# ---------------------------------------------------------------------------
# Utility commands (unchanged, operate on explicit paths)
# ---------------------------------------------------------------------------


@main.command()
@click.argument("input_dir", type=click.Path(exists=True))
def parse(input_dir: str) -> None:
    """Parse a notebook and output a JSON summary."""
    parser = NotebookParser()
    content = parser.parse(input_dir)

    summary = {
        "path": content.path,
        "num_cells": len(content.cells),
        "todo_code": sum(1 for c in content.cells if c.status.value == "todo_code"),
        "todo_markdown": sum(
            1 for c in content.cells if c.status.value == "todo_markdown"
        ),
        "kernel_spec": content.kernel_spec,
        "has_instructions": content.instructions is not None,
    }
    console.print_json(json.dumps(summary))


@main.command()
@click.argument("notebook_path", type=click.Path(exists=True))
@click.option(
    "--timeout", "-t", type=int, default=600, help="Timeout per cell in seconds."
)
@click.option("--kernel", "-k", type=str, default=None, help="Kernel name.")
def execute(notebook_path: str, timeout: int, kernel: str | None) -> None:
    """Execute a notebook via papermill."""
    executor = NotebookExecutor()
    result = executor.execute(notebook_path, timeout=timeout, kernel=kernel)
    console.print(f"[green]Executed:[/green] {result}")


@main.command(name="export")
@click.argument("notebook_path", type=click.Path(exists=True))
@click.option("--format", "fmt", type=click.Choice(["html"]), default="html")
@click.option("--output", "-o", type=click.Path(), default=None)
def export_cmd(notebook_path: str, fmt: str, output: str | None) -> None:
    """Export a notebook to HTML."""
    exporter = NotebookExporter()
    out = output if output else None
    result = exporter.export_html(notebook_path, out)
    console.print(f"[green]Exported ({fmt}):[/green] {result}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_notebook(directory: Path, suffix: str = ".ipynb") -> Path | None:
    """Find the first notebook matching *suffix* in *directory*."""
    if not directory.is_dir():
        return None
    for p in sorted(directory.iterdir()):
        if p.name.endswith(suffix):
            return p
    return None


def _find_latest_run(layout: ProjectLayout) -> Path:
    """Find the most recent run-NNN directory in output/."""
    import re

    pattern = re.compile(r"^run-(\d{3})$")
    best_n = 0
    best_dir = layout.output_dir / "run-001"
    if layout.output_dir.is_dir():
        for child in layout.output_dir.iterdir():
            if child.is_dir():
                m = pattern.match(child.name)
                if m and int(m.group(1)) > best_n:
                    best_n = int(m.group(1))
                    best_dir = child
    return best_dir
