"""Shared test fixtures for notebook-processor tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    """Return a temporary output directory."""
    output = tmp_path / "output"
    output.mkdir()
    return output


@pytest.fixture
def tmp_done(tmp_path: Path) -> Path:
    """Return a temporary done directory."""
    done = tmp_path / "done"
    done.mkdir()
    return done
