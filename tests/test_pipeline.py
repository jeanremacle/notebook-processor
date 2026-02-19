"""Tests for notebook_processor.pipeline."""

from __future__ import annotations

from pathlib import Path

import nbformat
import pytest

from notebook_processor.pipeline import ProcessingPipeline
from notebook_processor.solver import StubSolver


@pytest.fixture
def pipeline() -> ProcessingPipeline:
    return ProcessingPipeline()


@pytest.fixture
def demo_input(tmp_path: Path) -> Path:
    """Create a minimal input directory with a trivial notebook."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.cells.append(nbformat.v4.new_markdown_cell("# Test"))
    nb.cells.append(
        nbformat.v4.new_code_cell(
            "# TODO: implement\ndef greet():\n    raise NotImplementedError"
        )
    )
    nb.cells.append(nbformat.v4.new_code_cell("x = 1 + 1\nassert x == 2"))
    nbformat.write(nb, str(input_dir / "test_nb.ipynb"))

    (input_dir / "instructions.md").write_text("Complete the notebook.")

    return input_dir


class TestProcessingPipeline:
    def test_full_pipeline(
        self,
        pipeline: ProcessingPipeline,
        demo_input: Path,
        tmp_path: Path,
    ) -> None:
        output_dir = tmp_path / "output"
        done_dir = tmp_path / "done"
        solver = StubSolver()

        state = pipeline.run(demo_input, output_dir, done_dir, solver)

        assert "parse" in state.completed_steps
        assert "solve" in state.completed_steps
        assert "build" in state.completed_steps
        assert "execute" in state.completed_steps
        assert "export" in state.completed_steps
        assert "archive" in state.completed_steps
        assert state.errors == []

    def test_creates_completed_notebook(
        self,
        pipeline: ProcessingPipeline,
        demo_input: Path,
        tmp_path: Path,
    ) -> None:
        output_dir = tmp_path / "output"
        done_dir = tmp_path / "done"
        solver = StubSolver()

        pipeline.run(demo_input, output_dir, done_dir, solver)

        completed = output_dir / "test_nb_completed.ipynb"
        assert completed.exists()

    def test_creates_html_export(
        self,
        pipeline: ProcessingPipeline,
        demo_input: Path,
        tmp_path: Path,
    ) -> None:
        output_dir = tmp_path / "output"
        done_dir = tmp_path / "done"
        solver = StubSolver()

        pipeline.run(demo_input, output_dir, done_dir, solver)

        html = output_dir / "test_nb_completed.html"
        assert html.exists()
        assert "<html" in html.read_text(encoding="utf-8").lower()

    def test_archives_input(
        self,
        pipeline: ProcessingPipeline,
        demo_input: Path,
        tmp_path: Path,
    ) -> None:
        output_dir = tmp_path / "output"
        done_dir = tmp_path / "done"
        solver = StubSolver()

        pipeline.run(demo_input, output_dir, done_dir, solver)

        assert (done_dir / "test_nb.ipynb").exists()
        assert (done_dir / "instructions.md").exists()

    def test_saves_state(
        self,
        pipeline: ProcessingPipeline,
        demo_input: Path,
        tmp_path: Path,
    ) -> None:
        output_dir = tmp_path / "output"
        done_dir = tmp_path / "done"
        solver = StubSolver()

        pipeline.run(demo_input, output_dir, done_dir, solver)

        state_file = output_dir / "state.json"
        assert state_file.exists()

    def test_resume_from_state(
        self,
        pipeline: ProcessingPipeline,
        demo_input: Path,
        tmp_path: Path,
    ) -> None:
        output_dir = tmp_path / "output"
        done_dir = tmp_path / "done"
        solver = StubSolver()

        # Run first time
        pipeline.run(demo_input, output_dir, done_dir, solver)

        # Run again (should be idempotent since state is saved)
        state = pipeline.run(demo_input, output_dir, done_dir, solver)
        assert state.errors == []

    def test_pipeline_with_failing_execution(self, tmp_path: Path) -> None:
        """Pipeline should propagate errors from execution."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        nb = nbformat.v4.new_notebook()
        nb.metadata["kernelspec"] = {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        }
        nb.cells.append(
            nbformat.v4.new_code_cell("# TODO\nraise ValueError('intentional failure')")
        )
        nbformat.write(nb, str(input_dir / "fail.ipynb"))

        output_dir = tmp_path / "output"
        done_dir = tmp_path / "done"
        solver = StubSolver()
        pipeline = ProcessingPipeline()

        # StubSolver replaces the cell with "pass", so execution
        # should succeed since the NotImplementedError is replaced.
        state = pipeline.run(input_dir, output_dir, done_dir, solver)
        assert "execute" in state.completed_steps

    def test_pipeline_no_done_dir(
        self,
        pipeline: ProcessingPipeline,
        demo_input: Path,
        tmp_path: Path,
    ) -> None:
        """Archive step is skipped when done_dir is None."""
        output_dir = tmp_path / "output"
        solver = StubSolver()

        state = pipeline.run(demo_input, output_dir, None, solver)

        assert "archive" in state.completed_steps
        assert state.done_path is None
        # No done directory was created
        assert not (tmp_path / "done").exists()

    def test_run_project(
        self,
        pipeline: ProcessingPipeline,
        tmp_path: Path,
    ) -> None:
        """run_project uses ProjectLayout to resolve paths."""
        from notebook_processor.project_layout import ProjectLayout

        layout = ProjectLayout(tmp_path)
        layout.ensure_dirs()

        # Set up a notebook in the ingested directory
        nb = nbformat.v4.new_notebook()
        nb.metadata["kernelspec"] = {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        }
        nb.cells.append(nbformat.v4.new_code_cell("x = 1 + 1"))
        nbformat.write(nb, str(layout.ingested_dir / "test.ipynb"))

        solver = StubSolver()
        state = pipeline.run_project(layout, solver)

        assert "archive" in state.completed_steps
        assert state.done_path is None
        # Output should land in run-001
        assert (layout.output_dir / "run-001" / "test_completed.ipynb").exists()
