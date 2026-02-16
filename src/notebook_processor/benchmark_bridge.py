"""Integration bridge between notebook-processor and benchmark-framework."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _benchmark_available() -> bool:
    """Check if benchmark-framework is installed."""
    try:
        import benchmark_framework  # type: ignore[import-untyped]  # noqa: F401

        return True
    except ImportError:
        return False


def setup_benchmark(input_dir: str | Path) -> Path | None:
    """Set up benchmark configuration from notebook iterations.

    Scans for an iterations/ subdirectory in input_dir and creates
    benchmark configuration files (iterations.json, metrics.json,
    runs.json) if iterations are found.

    Args:
        input_dir: Path to the input directory.

    Returns:
        Path to the benchmark config directory, or None if no
        iterations found or benchmark-framework not installed.
    """
    if not _benchmark_available():
        logger.debug("benchmark-framework not installed, skipping")
        return None

    input_path = Path(input_dir)
    iterations_dir = input_path / "iterations"
    if not iterations_dir.exists():
        logger.debug("No iterations/ directory found, skipping benchmark")
        return None

    config_dir = input_path / ".benchmark"
    config_dir.mkdir(exist_ok=True)

    iterations = _discover_iterations(iterations_dir)
    if not iterations:
        return None

    _write_iterations_config(config_dir, iterations)
    _write_metrics_config(config_dir)
    _write_runs_config(config_dir, iterations)

    logger.info("Benchmark config created at %s", config_dir)
    return config_dir


def run_benchmark(config_dir: str | Path, output_dir: str | Path) -> str | None:
    """Execute a benchmark run and generate a comparison report.

    Args:
        config_dir: Path to benchmark configuration directory.
        output_dir: Path for the output report.

    Returns:
        The generated Markdown report, or None if not available.
    """
    if not _benchmark_available():
        return None

    from benchmark_framework.api import execute_run, generate_report  # type: ignore[import-untyped]  # noqa: I001

    config_path = Path(config_dir)
    output_path = Path(output_dir)

    runs_file = config_path / "runs.json"
    if not runs_file.exists():
        logger.warning("No runs.json found in %s", config_path)
        return None

    runs_data = json.loads(runs_file.read_text(encoding="utf-8"))
    for run_def in runs_data.get("runs", []):
        if run_def.get("status") == "pending":
            run_id: str = run_def["id"]
            logger.info("Executing benchmark run: %s", run_id)
            execute_run(run_id, config_path)

    report_path = output_path / "comparison_report.md"
    report: str = generate_report(config_path, report_path)
    logger.info("Benchmark report generated: %s", report_path)
    return report


def _discover_iterations(iterations_dir: Path) -> list[dict[str, Any]]:
    """Discover iteration directories and build iteration configs."""
    iterations: list[dict[str, Any]] = []
    for entry in sorted(iterations_dir.iterdir()):
        if not entry.is_dir():
            continue
        main_py = entry / "main.py"
        if not main_py.exists():
            logger.debug("Skipping %s (no main.py)", entry.name)
            continue

        iterations.append(
            {
                "id": entry.name,
                "name": entry.name.replace("_", " ").title(),
                "description": f"Iteration from {entry.name}",
                "approach": entry.name,
                "source_path": str(entry),
                "entry_point": "main.py",
                "parameters": {},
                "parent": None,
                "created_at": datetime.now(UTC).isoformat(),
                "tags": [],
            }
        )

    return iterations


def _write_iterations_config(
    config_dir: Path, iterations: list[dict[str, Any]]
) -> None:
    """Write iterations.json to config directory."""
    config = {"project": "notebook-benchmark", "iterations": iterations}
    (config_dir / "iterations.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )


def _write_metrics_config(config_dir: Path) -> None:
    """Write a default metrics.json with execution time metric."""
    config = {
        "metrics": [
            {
                "id": "exec_time",
                "name": "Execution Time",
                "description": "Wall-clock execution time",
                "type": "performance",
                "class": "benchmark_framework.metrics.timing.ExecutionTimeMetric",
                "higher_is_better": False,
                "unit": "seconds",
            }
        ]
    }
    (config_dir / "metrics.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )


def _write_runs_config(config_dir: Path, iterations: list[dict[str, Any]]) -> None:
    """Write runs.json to config directory."""
    config = {
        "runs": [
            {
                "id": "run-001",
                "name": "Notebook comparison",
                "description": "Compare notebook iterations",
                "iteration_ids": [it["id"] for it in iterations],
                "metric_ids": ["exec_time"],
                "status": "pending",
                "created_at": datetime.now(UTC).isoformat(),
            }
        ]
    }
    (config_dir / "runs.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )
