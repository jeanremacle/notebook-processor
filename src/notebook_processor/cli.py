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


@main.command()
@click.argument("input_dir", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output directory.",
)
@click.option(
    "--done",
    "-d",
    type=click.Path(),
    default=None,
    help="Done/archive directory.",
)
def process(input_dir: str, output: str | None, done: str | None) -> None:
    """Run the full processing pipeline."""
    input_path = Path(input_dir)
    output_path = Path(output) if output else input_path.parent / "output"
    done_path = Path(done) if done else input_path.parent / "done"

    solver = StubSolver()
    pipeline = ProcessingPipeline()

    console.print(f"[bold]Processing:[/bold] {input_path}")
    state = pipeline.run(input_path, output_path, done_path, solver)

    console.print(f"[green]Completed steps:[/green] {', '.join(state.completed_steps)}")
    if state.errors:
        console.print(f"[red]Errors:[/red] {state.errors}")


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


@main.command()
@click.argument("input_dir", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    required=True,
    help="Target package directory.",
)
def ingest(input_dir: str, output: str) -> None:
    """Ingest a raw assignment folder into a normalized package."""
    raw_path = Path(input_dir)
    target_path = Path(output)

    ingestor = PackageIngestor()

    console.print(f"[bold]Ingesting:[/bold] {raw_path} → {target_path}")
    manifest = ingestor.ingest(raw_path, target_path)

    analysis = manifest.notebook.analysis
    console.print(f"[green]Assets:[/green] {len(manifest.assets)} files")
    if analysis:
        console.print(f"[green]TODO markers:[/green] {len(analysis.todo_markers)}")
        console.print(f"[green]Images extracted:[/green] {analysis.embedded_images_count}")
        console.print(f"[green]Dependencies:[/green] {', '.join(analysis.dependencies) or 'none'}")
    console.print(f"[green]Manifest:[/green] {target_path / 'manifest.json'}")
