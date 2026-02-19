"""Tests for NotebookPreprocessor."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from notebook_processor.ingestion.notebook_preprocess import (
    NotebookPreprocessor,
)
from notebook_processor.ingestion.transformations import TransformationLogger
from notebook_processor.models import CellType


@pytest.fixture
def preprocessor() -> NotebookPreprocessor:
    return NotebookPreprocessor()


@pytest.fixture
def xform_logger() -> TransformationLogger:
    return TransformationLogger()


def _make_notebook(
    cells: list[dict[str, object]],
    kernel: str = "python3",
) -> dict[str, object]:
    """Build a minimal nbformat v4 notebook dict."""
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "name": kernel,
                "display_name": "Python 3",
                "language": "python",
            }
        },
        "cells": cells,
    }


def _code_cell(source: str, outputs: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "cell_type": "code",
        "source": source,
        "metadata": {},
        "execution_count": None,
        "id": "abc123",
        "outputs": outputs or [],
    }


def _md_cell(source: str) -> dict[str, object]:
    return {
        "cell_type": "markdown",
        "source": source,
        "metadata": {},
        "id": "def456",
    }


def _write_notebook(path: Path, nb_dict: dict[str, object]) -> None:
    path.write_text(json.dumps(nb_dict), encoding="utf-8")


class TestImageExtraction:
    def test_extract_base64_from_output(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        # Create a 1x1 red PNG pixel (minimal valid PNG)
        png_data = base64.b64encode(
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        ).decode()

        nb = _make_notebook([
            _code_cell("print('hello')", outputs=[{
                "output_type": "display_data",
                "data": {"image/png": png_data},
                "metadata": {},
            }]),
        ])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)

        assert analysis.embedded_images_count == 1
        assert analysis.embedded_images_total_bytes > 0
        assert (pkg_dir / "images").is_dir()

    def test_extract_base64_from_markdown(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        b64 = base64.b64encode(b"\x89PNG fake image data").decode()
        md_source = f"# Output\n![Result](data:image/png;base64,{b64})"

        nb = _make_notebook([_md_cell(md_source)])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)

        assert analysis.embedded_images_count == 1

    def test_no_images(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([_code_cell("x = 1")])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert analysis.embedded_images_count == 0
        assert analysis.embedded_images_total_bytes == 0


class TestTodoDetection:
    def test_todo_comment(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([_code_cell("# TODO: implement this")])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert len(analysis.todo_markers) == 1
        assert analysis.todo_markers[0].cell_type == CellType.CODE

    def test_not_implemented_error(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([_code_cell("raise NotImplementedError")])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert len(analysis.todo_markers) == 1

    def test_your_code_here(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([_code_cell("# YOUR CODE HERE")])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert len(analysis.todo_markers) == 1

    def test_jhu_prompt_marker(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([
            _code_cell('system_prompt = "<-- YOUR SYSTEM PROMPT GOES HERE -->"'),
        ])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert len(analysis.todo_markers) == 1
        assert analysis.todo_markers[0].variable_name == "system_prompt"

    def test_markdown_answer_here(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([_md_cell("**Your answer here**")])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert len(analysis.todo_markers) == 1
        assert analysis.todo_markers[0].cell_type == CellType.MARKDOWN

    def test_no_markers(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([_code_cell("x = 42")])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert len(analysis.todo_markers) == 0


class TestDependencyDetection:
    def test_detects_imports(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([
            _code_cell("import pandas\nfrom openai import ChatCompletion"),
        ])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert "pandas" in analysis.dependencies
        assert "openai" in analysis.dependencies
        assert "openai" in analysis.api_dependencies

    def test_detects_pip_install(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([_code_cell("!pip install transformers")])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert "transformers" in analysis.dependencies

    def test_filters_stdlib(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([_code_cell("import os\nimport json\nimport pandas")])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert "os" not in analysis.dependencies
        assert "json" not in analysis.dependencies
        assert "pandas" in analysis.dependencies


class TestHardcodedPaths:
    def test_detects_your_file_location(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([
            _code_cell('df = pd.read_csv("your_file_location")'),
        ])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert len(analysis.hardcoded_paths) == 1
        assert "your_file_location" in analysis.hardcoded_paths[0]

    def test_detects_csv_paths(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([_code_cell("df = pd.read_csv('data.csv')")])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert len(analysis.hardcoded_paths) == 1


class TestSaveNotebook:
    def test_saves_cleaned_and_original(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([_code_cell("x = 1")])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        preprocessor.preprocess(nb_path, pkg_dir, xform_logger)

        assert (pkg_dir / "notebook.ipynb").exists()
        assert (pkg_dir / "notebook.ipynb.orig").exists()


class TestKernelSpec:
    def test_extracts_kernel(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([_code_cell("x = 1")], kernel="python3")
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert analysis.kernel_spec == "python3"

    def test_cell_type_counts(
        self,
        preprocessor: NotebookPreprocessor,
        xform_logger: TransformationLogger,
        tmp_path: Path,
    ) -> None:
        nb = _make_notebook([
            _code_cell("x = 1"),
            _code_cell("y = 2"),
            _md_cell("# Title"),
        ])
        nb_path = tmp_path / "raw" / "test.ipynb"
        nb_path.parent.mkdir(parents=True)
        _write_notebook(nb_path, nb)

        pkg_dir = tmp_path / "pkg"
        pkg_dir.mkdir()

        analysis = preprocessor.preprocess(nb_path, pkg_dir, xform_logger)
        assert analysis.total_cells == 3
        assert analysis.cell_type_counts["code"] == 2
        assert analysis.cell_type_counts["markdown"] == 1
