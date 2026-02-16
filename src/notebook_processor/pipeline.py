"""Full pipeline orchestration for notebook processing."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from notebook_processor.archiver import NotebookArchiver
from notebook_processor.builder import NotebookBuilder
from notebook_processor.executor import NotebookExecutor
from notebook_processor.exporter import NotebookExporter
from notebook_processor.models import PipelineState
from notebook_processor.parser import NotebookParser
from notebook_processor.solver import NotebookSolver

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    """Orchestrates the full notebook processing workflow."""

    def __init__(self) -> None:
        self._parser = NotebookParser()
        self._builder = NotebookBuilder()
        self._executor = NotebookExecutor()
        self._exporter = NotebookExporter()
        self._archiver = NotebookArchiver()

    def run(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        done_dir: str | Path,
        solver: NotebookSolver,
    ) -> PipelineState:
        """Run the full processing pipeline.

        Args:
            input_dir: Directory with the source notebook.
            output_dir: Directory for processed output.
            done_dir: Directory for archived originals.
            solver: Solver to complete TODO cells.

        Returns:
            Final pipeline state.
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        done_path = Path(done_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        state = self._load_or_create_state(input_path, output_path, done_path)

        try:
            if "parse" not in state.completed_steps:
                state = state.model_copy(update={"current_step": "parse"})
                content = self._parser.parse(input_path)
                self._save_state(state, output_path)

                if "solve" not in state.completed_steps:
                    state = state.model_copy(update={"current_step": "solve"})
                    content = solver.solve(content)
                    state = state.model_copy(
                        update={
                            "completed_steps": [
                                *state.completed_steps,
                                "parse",
                                "solve",
                            ]
                        }
                    )
                    self._save_state(state, output_path)
            else:
                content = self._parser.parse(input_path)
                if "solve" not in state.completed_steps:
                    state = state.model_copy(update={"current_step": "solve"})
                    content = solver.solve(content)
                    state = state.model_copy(
                        update={
                            "completed_steps": [
                                *state.completed_steps,
                                "solve",
                            ]
                        }
                    )
                    self._save_state(state, output_path)

            nb_stem = Path(content.path).stem
            output_nb = output_path / f"{nb_stem}_completed.ipynb"

            if "build" not in state.completed_steps:
                state = state.model_copy(update={"current_step": "build"})
                self._builder.build(content, output_nb)
                state = state.model_copy(
                    update={
                        "completed_steps": [
                            *state.completed_steps,
                            "build",
                        ]
                    }
                )
                self._save_state(state, output_path)

            if "execute" not in state.completed_steps:
                state = state.model_copy(update={"current_step": "execute"})
                self._executor.execute(output_nb)
                state = state.model_copy(
                    update={
                        "completed_steps": [
                            *state.completed_steps,
                            "execute",
                        ]
                    }
                )
                self._save_state(state, output_path)

            if "export" not in state.completed_steps:
                state = state.model_copy(update={"current_step": "export"})
                html_path = output_path / f"{nb_stem}_completed.html"
                self._exporter.export_html(output_nb, html_path)
                state = state.model_copy(
                    update={
                        "completed_steps": [
                            *state.completed_steps,
                            "export",
                        ]
                    }
                )
                self._save_state(state, output_path)

            if "archive" not in state.completed_steps:
                state = state.model_copy(update={"current_step": "archive"})
                self._archiver.archive(input_path, done_path)
                state = state.model_copy(
                    update={
                        "completed_steps": [
                            *state.completed_steps,
                            "archive",
                        ]
                    }
                )
                self._save_state(state, output_path)

        except Exception as exc:
            state = state.model_copy(update={"errors": [*state.errors, str(exc)]})
            self._save_state(state, output_path)
            logger.error("Pipeline failed at step '%s': %s", state.current_step, exc)
            raise

        logger.info("Pipeline completed successfully")
        self._save_state(state, output_path)
        return state

    def _load_or_create_state(
        self,
        input_path: Path,
        output_path: Path,
        done_path: Path,
    ) -> PipelineState:
        """Load existing state or create a new one."""
        state_file = output_path / "state.json"
        if state_file.exists():
            data = json.loads(state_file.read_text(encoding="utf-8"))
            return PipelineState.model_validate(data)
        return PipelineState(
            input_path=str(input_path),
            output_path=str(output_path),
            done_path=str(done_path),
            current_step="parse",
        )

    def _save_state(self, state: PipelineState, output_path: Path) -> None:
        """Persist pipeline state to disk."""
        state_file = output_path / "state.json"
        state_file.write_text(state.model_dump_json(indent=2), encoding="utf-8")
