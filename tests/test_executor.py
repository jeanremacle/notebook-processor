"""Tests for notebook_processor.executor."""

from __future__ import annotations

from pathlib import Path

import nbformat
import pytest

from notebook_processor.executor import ExecutionError, NotebookExecutor


@pytest.fixture
def executor() -> NotebookExecutor:
    return NotebookExecutor()


def _create_notebook(path: Path, cells: list[str]) -> Path:
    """Create a simple notebook with code cells."""
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    for code in cells:
        nb.cells.append(nbformat.v4.new_code_cell(code))
    nbformat.write(nb, str(path))
    return path


class TestNotebookExecutor:
    def test_execute_simple_notebook(
        self, executor: NotebookExecutor, tmp_path: Path
    ) -> None:
        nb_path = _create_notebook(
            tmp_path / "test.ipynb", ["x = 1 + 1", "assert x == 2"]
        )
        result = executor.execute(nb_path)
        assert result.exists()

        nb = nbformat.read(str(result), as_version=4)
        # Cells should have been executed (execution_count set)
        assert nb.cells[0].execution_count is not None

    def test_execute_captures_output(
        self, executor: NotebookExecutor, tmp_path: Path
    ) -> None:
        nb_path = _create_notebook(tmp_path / "test.ipynb", ["print('hello world')"])
        result = executor.execute(nb_path)
        nb = nbformat.read(str(result), as_version=4)
        outputs = nb.cells[0].outputs
        assert len(outputs) > 0
        assert any("hello world" in str(o) for o in outputs)

    def test_execute_file_not_found(
        self, executor: NotebookExecutor, tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError):
            executor.execute(tmp_path / "nonexistent.ipynb")

    def test_execute_with_error_raises(
        self, executor: NotebookExecutor, tmp_path: Path
    ) -> None:
        nb_path = _create_notebook(
            tmp_path / "test.ipynb",
            ["raise ValueError('test error')"],
        )
        with pytest.raises(ExecutionError):
            executor.execute(nb_path)

    def test_execute_with_timeout(
        self, executor: NotebookExecutor, tmp_path: Path
    ) -> None:
        nb_path = _create_notebook(tmp_path / "test.ipynb", ["x = 42"])
        result = executor.execute(nb_path, timeout=30)
        assert result.exists()

    def test_execute_multi_cell(
        self, executor: NotebookExecutor, tmp_path: Path
    ) -> None:
        nb_path = _create_notebook(
            tmp_path / "test.ipynb",
            [
                "a = 10",
                "b = a * 2",
                "assert b == 20",
            ],
        )
        result = executor.execute(nb_path)
        nb = nbformat.read(str(result), as_version=4)
        assert all(c.execution_count is not None for c in nb.cells)

    def test_kernel_launch_failure_raises_execution_error(
        self, executor: NotebookExecutor, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A kernel launch failure (e.g. stale kernel path) should raise ExecutionError."""
        nb_path = _create_notebook(tmp_path / "test.ipynb", ["x = 1"])

        # Simulate a kernel launch failure by making pm.execute_notebook
        # raise FileNotFoundError (as happens with stale kernel specs)
        def _fake_execute(**kwargs: object) -> None:
            raise FileNotFoundError("No such file or directory: '/stale/path/python3'")

        import papermill as pm

        monkeypatch.setattr(pm, "execute_notebook", _fake_execute)

        with pytest.raises(ExecutionError, match="stale/path"):
            executor.execute(nb_path)

    def test_ensure_kernel_called(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_ensure_kernel is called before execution."""
        nb_path = _create_notebook(tmp_path / "test.ipynb", ["x = 1"])

        called = {"count": 0}
        original_ensure = NotebookExecutor._ensure_kernel

        @staticmethod  # type: ignore[misc]
        def _tracking_ensure(kernel_name: str | None) -> None:
            called["count"] += 1
            original_ensure(kernel_name)

        monkeypatch.setattr(NotebookExecutor, "_ensure_kernel", _tracking_ensure)

        executor = NotebookExecutor()
        executor.execute(nb_path)
        assert called["count"] == 1
