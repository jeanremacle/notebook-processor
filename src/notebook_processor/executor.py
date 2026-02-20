"""Execute notebooks via papermill."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import papermill as pm

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Raised when notebook execution fails."""


class NotebookExecutor:
    """Executes notebooks using papermill."""

    def execute(
        self,
        notebook_path: str | Path,
        *,
        timeout: int = 600,
        kernel: str | None = None,
    ) -> Path:
        """Execute a notebook and return the path to the executed version.

        Args:
            notebook_path: Path to the .ipynb file to execute.
            timeout: Maximum execution time per cell in seconds.
            kernel: Kernel name to use. If None, uses the notebook's
                default kernel.

        Returns:
            Path to the executed notebook (overwrites in place).

        Raises:
            ExecutionError: If notebook execution fails.
        """
        nb_path = Path(notebook_path)
        if not nb_path.exists():
            msg = f"Notebook not found: {nb_path}"
            raise FileNotFoundError(msg)

        logger.info("Executing notebook: %s", nb_path)

        # Ensure the kernel uses the current environment's Python by
        # registering a temporary ipykernel pointing to sys.executable.
        # This avoids stale kernel specs that reference non-existent venvs.
        self._ensure_kernel(kernel)

        kwargs: dict[str, Any] = {
            "input_path": str(nb_path),
            "output_path": str(nb_path),
            "request_save_on_cell_execute": True,
        }
        if kernel:
            kwargs["kernel_name"] = kernel
        if timeout:
            kwargs["execution_timeout"] = timeout

        try:
            pm.execute_notebook(**kwargs)
        except pm.PapermillExecutionError as exc:
            logger.error("Notebook execution failed: %s", exc)
            raise ExecutionError(str(exc)) from exc
        except Exception as exc:
            logger.error("Kernel launch or execution error: %s", exc)
            raise ExecutionError(str(exc)) from exc

        logger.info("Notebook executed successfully: %s", nb_path)
        return nb_path

    @staticmethod
    def _ensure_kernel(kernel_name: str | None) -> None:
        """Ensure the python3 kernel points to the current interpreter.

        If the registered ``python3`` kernel points to a Python binary
        that doesn't exist, re-register it using the current
        ``sys.executable``.  This is a no-op when the kernel is already
        correct or when a non-default kernel is requested.
        """
        if kernel_name is not None and kernel_name != "python3":
            return

        try:
            from jupyter_client.kernelspec import KernelSpecManager

            ksm = KernelSpecManager()
            spec = ksm.get_kernel_spec("python3")
            python_path = spec.argv[0] if spec.argv else ""

            if python_path and not Path(python_path).exists():
                logger.warning(
                    "Registered python3 kernel points to missing interpreter: %s",
                    python_path,
                )
                logger.info(
                    "Re-registering python3 kernel with current interpreter: %s",
                    sys.executable,
                )
                _install_kernel()
        except Exception:
            # If we can't check, try to install just in case
            logger.debug("Could not verify kernel spec, ensuring kernel is installed")
            _install_kernel()


def _install_kernel() -> None:
    """Install an ipykernel for the current Python interpreter."""
    try:
        from ipykernel.kernelspec import install

        install(user=True, kernel_name="python3", display_name="Python 3 (ipykernel)")
        logger.info("Installed python3 kernel for %s", sys.executable)
    except Exception as exc:
        logger.warning("Could not install kernel: %s", exc)
