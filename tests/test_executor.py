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


class _FakeKSM:
    """Fake KernelSpecManager that returns a canned kernel spec."""

    def __init__(self, argv: list[str]) -> None:
        self._argv = argv

    def get_kernel_spec(self, _kernel_name: str) -> object:
        from types import SimpleNamespace

        return SimpleNamespace(argv=self._argv)


class TestEnsureKernel:
    """Tests for _ensure_kernel stale-kernel-spec detection (bug #1).

    The real bug: the system-level python3 kernel spec pointed to a
    deleted .venv interpreter.  _ensure_kernel detects this and calls
    _install_kernel to re-register.
    """

    def test_stale_kernel_triggers_reinstall(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A kernel spec pointing to a non-existent interpreter triggers _install_kernel."""
        import jupyter_client.kernelspec as _jc_ks

        import notebook_processor.executor as _mod

        # KernelSpecManager is imported inside _ensure_kernel, so patch
        # on the jupyter_client.kernelspec module where it's imported from.
        monkeypatch.setattr(
            _jc_ks,
            "KernelSpecManager",
            lambda: _FakeKSM(["/nonexistent/stale/venv/bin/python3"]),
        )

        installed = {"called": False}

        def _fake_install() -> None:
            installed["called"] = True

        monkeypatch.setattr(_mod, "_install_kernel", _fake_install)

        NotebookExecutor._ensure_kernel(None)
        assert installed["called"], "_install_kernel should be called for a stale kernel path"

    def test_valid_kernel_skips_reinstall(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A kernel spec pointing to the current interpreter does NOT trigger reinstall."""
        import sys

        import jupyter_client.kernelspec as _jc_ks

        import notebook_processor.executor as _mod

        monkeypatch.setattr(
            _jc_ks,
            "KernelSpecManager",
            lambda: _FakeKSM([sys.executable]),
        )

        installed = {"called": False}

        def _fake_install() -> None:
            installed["called"] = True

        monkeypatch.setattr(_mod, "_install_kernel", _fake_install)

        NotebookExecutor._ensure_kernel(None)
        assert not installed["called"], "_install_kernel should NOT be called for a valid kernel"

    def test_non_python3_kernel_skips_check(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-python3 kernel name skips the kernel check entirely."""
        import notebook_processor.executor as _mod

        installed = {"called": False}

        def _fake_install() -> None:
            installed["called"] = True

        monkeypatch.setattr(_mod, "_install_kernel", _fake_install)

        NotebookExecutor._ensure_kernel("julia-1.9")
        assert not installed["called"], "Non-python3 kernels should skip the check"

    def test_python3_kernel_name_triggers_check(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicitly passing kernel_name='python3' still runs the check."""
        import jupyter_client.kernelspec as _jc_ks

        import notebook_processor.executor as _mod

        monkeypatch.setattr(
            _jc_ks,
            "KernelSpecManager",
            lambda: _FakeKSM(["/nonexistent/old/venv/bin/python3"]),
        )

        installed = {"called": False}

        def _fake_install() -> None:
            installed["called"] = True

        monkeypatch.setattr(_mod, "_install_kernel", _fake_install)

        NotebookExecutor._ensure_kernel("python3")
        assert installed["called"], "_install_kernel should be called for stale python3 kernel"

    def test_ksm_exception_triggers_fallback_install(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If KernelSpecManager raises, _install_kernel is called as fallback."""
        import jupyter_client.kernelspec as _jc_ks

        import notebook_processor.executor as _mod

        def _broken_ksm() -> None:
            raise RuntimeError("Kernel spec database corrupted")

        monkeypatch.setattr(_jc_ks, "KernelSpecManager", _broken_ksm)

        installed = {"called": False}

        def _fake_install() -> None:
            installed["called"] = True

        monkeypatch.setattr(_mod, "_install_kernel", _fake_install)

        NotebookExecutor._ensure_kernel(None)
        assert installed["called"], "_install_kernel should be called as fallback on exception"
