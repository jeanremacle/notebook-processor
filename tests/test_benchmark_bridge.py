"""Tests for notebook_processor.benchmark_bridge."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from notebook_processor.benchmark_bridge import (
    _benchmark_available,
    _discover_iterations,
    setup_benchmark,
)


class TestBenchmarkAvailable:
    def test_is_available(self) -> None:
        assert _benchmark_available() is True

    def test_not_available_when_missing(self) -> None:
        with patch.dict("sys.modules", {"benchmark_framework": None}):
            # When the module is set to None, import raises ImportError
            assert _benchmark_available() is False


class TestDiscoverIterations:
    def test_finds_iterations_with_main_py(self, tmp_path: Path) -> None:
        iterations_dir = tmp_path / "iterations"
        v1 = iterations_dir / "v1_baseline"
        v1.mkdir(parents=True)
        (v1 / "main.py").write_text("print('v1')")

        v2 = iterations_dir / "v2_optimized"
        v2.mkdir()
        (v2 / "main.py").write_text("print('v2')")

        result = _discover_iterations(iterations_dir)
        assert len(result) == 2
        assert result[0]["id"] == "v1_baseline"
        assert result[1]["id"] == "v2_optimized"

    def test_skips_dirs_without_main_py(self, tmp_path: Path) -> None:
        iterations_dir = tmp_path / "iterations"
        (iterations_dir / "v1").mkdir(parents=True)
        (iterations_dir / "v1" / "other.py").write_text("x = 1")

        result = _discover_iterations(iterations_dir)
        assert len(result) == 0

    def test_skips_files(self, tmp_path: Path) -> None:
        iterations_dir = tmp_path / "iterations"
        iterations_dir.mkdir()
        (iterations_dir / "readme.txt").write_text("info")

        result = _discover_iterations(iterations_dir)
        assert len(result) == 0

    def test_empty_dir(self, tmp_path: Path) -> None:
        iterations_dir = tmp_path / "iterations"
        iterations_dir.mkdir()
        result = _discover_iterations(iterations_dir)
        assert len(result) == 0


class TestSetupBenchmark:
    def test_no_iterations_dir(self, tmp_path: Path) -> None:
        result = setup_benchmark(tmp_path)
        assert result is None

    def test_creates_config(self, tmp_path: Path) -> None:
        iterations_dir = tmp_path / "iterations"
        v1 = iterations_dir / "v1"
        v1.mkdir(parents=True)
        (v1 / "main.py").write_text("print('hello')")

        config_dir = setup_benchmark(tmp_path)
        assert config_dir is not None
        assert (config_dir / "iterations.json").exists()
        assert (config_dir / "metrics.json").exists()
        assert (config_dir / "runs.json").exists()

    def test_iterations_json_content(self, tmp_path: Path) -> None:
        iterations_dir = tmp_path / "iterations"
        v1 = iterations_dir / "v1"
        v1.mkdir(parents=True)
        (v1 / "main.py").write_text("print('hi')")

        config_dir = setup_benchmark(tmp_path)
        assert config_dir is not None
        data = json.loads((config_dir / "iterations.json").read_text(encoding="utf-8"))
        assert data["project"] == "notebook-benchmark"
        assert len(data["iterations"]) == 1
        assert data["iterations"][0]["id"] == "v1"

    def test_metrics_json_has_exec_time(self, tmp_path: Path) -> None:
        iterations_dir = tmp_path / "iterations"
        v1 = iterations_dir / "v1"
        v1.mkdir(parents=True)
        (v1 / "main.py").write_text("x = 1")

        config_dir = setup_benchmark(tmp_path)
        assert config_dir is not None
        data = json.loads((config_dir / "metrics.json").read_text(encoding="utf-8"))
        assert data["metrics"][0]["id"] == "exec_time"

    def test_runs_json_references_iterations(self, tmp_path: Path) -> None:
        iterations_dir = tmp_path / "iterations"
        for name in ["v1", "v2"]:
            d = iterations_dir / name
            d.mkdir(parents=True)
            (d / "main.py").write_text(f"print('{name}')")

        config_dir = setup_benchmark(tmp_path)
        assert config_dir is not None
        data = json.loads((config_dir / "runs.json").read_text(encoding="utf-8"))
        run = data["runs"][0]
        assert "v1" in run["iteration_ids"]
        assert "v2" in run["iteration_ids"]

    def test_returns_none_when_framework_missing(self, tmp_path: Path) -> None:
        iterations_dir = tmp_path / "iterations"
        v1 = iterations_dir / "v1"
        v1.mkdir(parents=True)
        (v1 / "main.py").write_text("x = 1")

        with patch(
            "notebook_processor.benchmark_bridge._benchmark_available",
            return_value=False,
        ):
            result = setup_benchmark(tmp_path)
        assert result is None

    def test_returns_none_for_empty_iterations(self, tmp_path: Path) -> None:
        iterations_dir = tmp_path / "iterations"
        iterations_dir.mkdir()
        result = setup_benchmark(tmp_path)
        assert result is None
