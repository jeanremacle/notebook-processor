"""Execute notebooks via papermill."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import papermill as pm  # type: ignore[import-untyped]

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

        logger.info("Notebook executed successfully: %s", nb_path)
        return nb_path
