"""Tests for notebook_processor.cli."""

from __future__ import annotations

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

    def test_process_command(self, tmp_path: Path) -> None:
        input_dir = _create_input_dir(tmp_path)
        output_dir = tmp_path / "output"
        done_dir = tmp_path / "done"
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "process",
                str(input_dir),
                "--output",
                str(output_dir),
                "--done",
                str(done_dir),
            ],
        )
        assert result.exit_code == 0
        assert (output_dir / "test_completed.ipynb").exists()

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
        raw = tmp_path / "raw"
        raw.mkdir()

        # Minimal notebook
        nb = nbformat.v4.new_notebook()
        nb.metadata["kernelspec"] = {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        }
        nb.cells.append(nbformat.v4.new_code_cell("# TODO: implement"))
        nbformat.write(nb, str(raw / "hw.ipynb"))

        target = tmp_path / "pkg"
        runner = CliRunner()
        result = runner.invoke(
            main, ["ingest", str(raw), "--output", str(target)]
        )
        assert result.exit_code == 0
        assert "Assets" in result.output
        assert (target / "manifest.json").exists()
