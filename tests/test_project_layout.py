"""Tests for ProjectLayout."""

from __future__ import annotations

from pathlib import Path

from notebook_processor.project_layout import ProjectLayout


class TestRootResolution:
    def test_root_from_project_dir(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        assert layout.root == tmp_path.resolve()

    def test_root_from_input_subdir(self, tmp_path: Path) -> None:
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        layout = ProjectLayout(input_dir)
        assert layout.root == tmp_path.resolve()

    def test_root_from_non_input_subdir(self, tmp_path: Path) -> None:
        """A dir not named 'input' is treated as root itself."""
        other = tmp_path / "other"
        other.mkdir()
        layout = ProjectLayout(other)
        assert layout.root == other.resolve()


class TestPathProperties:
    def test_input_dir(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        assert layout.input_dir == tmp_path.resolve() / "input"

    def test_ingested_dir(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        assert layout.ingested_dir == tmp_path.resolve() / "ingested"

    def test_output_dir(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        assert layout.output_dir == tmp_path.resolve() / "output"


class TestRunDir:
    def test_custom_name(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        assert layout.run_dir("my-run") == layout.output_dir / "my-run"

    def test_auto_sequential_empty(self, tmp_path: Path) -> None:
        """First auto run in an empty output dir is run-001."""
        layout = ProjectLayout(tmp_path)
        layout.ensure_dirs()
        assert layout.run_dir() == layout.output_dir / "run-001"

    def test_auto_sequential_existing(self, tmp_path: Path) -> None:
        """Next run after run-001 is run-002."""
        layout = ProjectLayout(tmp_path)
        layout.ensure_dirs()
        (layout.output_dir / "run-001").mkdir()
        assert layout.run_dir() == layout.output_dir / "run-002"

    def test_auto_sequential_gap(self, tmp_path: Path) -> None:
        """If run-001 and run-003 exist, next is run-004."""
        layout = ProjectLayout(tmp_path)
        layout.ensure_dirs()
        (layout.output_dir / "run-001").mkdir()
        (layout.output_dir / "run-003").mkdir()
        assert layout.run_dir() == layout.output_dir / "run-004"

    def test_auto_sequential_no_output_dir(self, tmp_path: Path) -> None:
        """If output/ doesn't exist yet, first run is run-001."""
        layout = ProjectLayout(tmp_path)
        assert layout.run_dir() == layout.output_dir / "run-001"

    def test_non_run_dirs_ignored(self, tmp_path: Path) -> None:
        """Directories not matching run-NNN are ignored."""
        layout = ProjectLayout(tmp_path)
        layout.ensure_dirs()
        (layout.output_dir / "custom-run").mkdir()
        (layout.output_dir / "run-002").mkdir()
        assert layout.run_dir() == layout.output_dir / "run-003"


class TestHasLooseFiles:
    def test_empty_root(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        assert not layout.has_loose_files()

    def test_only_canonical_dirs(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        layout.ensure_dirs()
        assert not layout.has_loose_files()

    def test_loose_file(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        layout.ensure_dirs()
        (tmp_path / "homework.ipynb").write_text("{}")
        assert layout.has_loose_files()

    def test_loose_dir(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        layout.ensure_dirs()
        (tmp_path / "data").mkdir()
        assert layout.has_loose_files()

    def test_nonexistent_root(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path / "nope")
        assert not layout.has_loose_files()


class TestInputAlreadyPopulated:
    def test_no_input_dir(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        assert not layout.input_already_populated()

    def test_empty_input_dir(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        layout.ensure_dirs()
        assert not layout.input_already_populated()

    def test_populated_input_dir(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        layout.ensure_dirs()
        (layout.input_dir / "notebook.ipynb").write_text("{}")
        assert layout.input_already_populated()


class TestEnsureDirs:
    def test_creates_all_dirs(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        layout.ensure_dirs()
        assert layout.input_dir.is_dir()
        assert layout.ingested_dir.is_dir()
        assert layout.output_dir.is_dir()

    def test_idempotent(self, tmp_path: Path) -> None:
        layout = ProjectLayout(tmp_path)
        layout.ensure_dirs()
        layout.ensure_dirs()
        assert layout.input_dir.is_dir()
