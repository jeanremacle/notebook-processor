"""Tests for notebook_processor.cli."""

from __future__ import annotations

import json
from pathlib import Path

import nbformat
from click.testing import CliRunner

from notebook_processor.cli import main


def _create_input_dir(base: Path) -> Path:
    """Create a minimal input directory for CLI tests."""
    input_dir = base / "input"
    input_dir.mkdir()
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.cells.append(nbformat.v4.new_markdown_cell("# Test"))
    nb.cells.append(nbformat.v4.new_code_cell("x = 1\nprint(x)"))
    nbformat.write(nb, str(input_dir / "test.ipynb"))
    return input_dir


def _create_project_dir(base: Path) -> Path:
    """Create a project root with loose files for unified-convention commands."""
    project = base / "project"
    project.mkdir()

    nb_data = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "name": "python3",
                "display_name": "Python 3",
                "language": "python",
            }
        },
        "cells": [
            {
                "cell_type": "code",
                "source": "# TODO: implement\nx = 42",
                "metadata": {},
                "execution_count": None,
                "id": "cell-1",
                "outputs": [],
            }
        ],
    }
    (project / "homework.ipynb").write_text(
        json.dumps(nb_data), encoding="utf-8"
    )
    (project / "instructions.md").write_text("# HW\n", encoding="utf-8")
    return project


class TestCLI:
    def test_main_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Notebook Processor" in result.output

    def test_parse_command(self, tmp_path: Path) -> None:
        input_dir = _create_input_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["parse", str(input_dir)])
        assert result.exit_code == 0
        assert "num_cells" in result.output

    def test_execute_command(self, tmp_path: Path) -> None:
        nb = nbformat.v4.new_notebook()
        nb.metadata["kernelspec"] = {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        }
        nb.cells.append(nbformat.v4.new_code_cell("x = 42"))
        nb_path = tmp_path / "test.ipynb"
        nbformat.write(nb, str(nb_path))

        runner = CliRunner()
        result = runner.invoke(main, ["execute", str(nb_path)])
        assert result.exit_code == 0
        assert "Executed" in result.output

    def test_export_command(self, tmp_path: Path) -> None:
        nb = nbformat.v4.new_notebook()
        nb.cells.append(nbformat.v4.new_code_cell("x = 1"))
        nb_path = tmp_path / "test.ipynb"
        nbformat.write(nb, str(nb_path))

        runner = CliRunner()
        result = runner.invoke(main, ["export", str(nb_path)])
        assert result.exit_code == 0
        assert "Exported" in result.output
        assert (tmp_path / "test.html").exists()

    def test_parse_nonexistent_dir(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["parse", "/nonexistent/path"])
        assert result.exit_code != 0

    def test_ingest_command(self, tmp_path: Path) -> None:
        project = _create_project_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["ingest", str(project)])
        assert result.exit_code == 0
        assert "Assets" in result.output
        assert (project / "ingested" / "manifest.json").exists()

    def test_process_command(self, tmp_path: Path) -> None:
        project = _create_project_dir(tmp_path)
        runner = CliRunner()
        # First ingest
        runner.invoke(main, ["ingest", str(project)])
        # Then process
        result = runner.invoke(main, ["process", str(project)])
        assert result.exit_code == 0
        assert "Completed steps" in result.output
        assert (project / "output" / "run-001").is_dir()

    def test_run_command(self, tmp_path: Path) -> None:
        project = _create_project_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["run", str(project)])
        assert result.exit_code == 0
        assert "Ingested" in result.output
        assert "Completed steps" in result.output
        # Both ingested and output should exist
        assert (project / "ingested" / "manifest.json").exists()
        assert (project / "output" / "run-001").is_dir()

    def test_process_sequential_naming(self, tmp_path: Path) -> None:
        project = _create_project_dir(tmp_path)
        runner = CliRunner()

        # First run
        runner.invoke(main, ["run", str(project)])
        assert (project / "output" / "run-001").is_dir()

        # Second process
        result = runner.invoke(main, ["process", str(project)])
        assert result.exit_code == 0
        assert (project / "output" / "run-002").is_dir()

    def test_validate_command(self, tmp_path: Path) -> None:
        project = _create_project_dir(tmp_path)
        runner = CliRunner()

        # First run the full pipeline
        result = runner.invoke(main, ["run", str(project)])
        assert result.exit_code == 0

        # Then validate
        result = runner.invoke(
            main, ["validate", str(project), "--name", "run-001"]
        )
        assert result.exit_code == 0
        assert "validated.html" in result.output
        assert (project / "output" / "run-001" / "validated.html").exists()
