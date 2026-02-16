"""Tests for notebook_processor.archiver."""

from __future__ import annotations

from pathlib import Path

import pytest

from notebook_processor.archiver import NotebookArchiver


@pytest.fixture
def archiver() -> NotebookArchiver:
    return NotebookArchiver()


class TestNotebookArchiver:
    def test_archive_copies_files(
        self, archiver: NotebookArchiver, tmp_path: Path
    ) -> None:
        src = tmp_path / "input"
        src.mkdir()
        (src / "file.txt").write_text("content")

        dst = tmp_path / "done"
        archiver.archive(src, dst)

        assert (dst / "file.txt").exists()
        assert (dst / "file.txt").read_text() == "content"

    def test_archive_preserves_structure(
        self, archiver: NotebookArchiver, tmp_path: Path
    ) -> None:
        src = tmp_path / "input"
        (src / "sub" / "dir").mkdir(parents=True)
        (src / "a.txt").write_text("a")
        (src / "sub" / "b.txt").write_text("b")
        (src / "sub" / "dir" / "c.txt").write_text("c")

        dst = tmp_path / "done"
        archiver.archive(src, dst)

        assert (dst / "a.txt").read_text() == "a"
        assert (dst / "sub" / "b.txt").read_text() == "b"
        assert (dst / "sub" / "dir" / "c.txt").read_text() == "c"

    def test_archive_creates_done_dir(
        self, archiver: NotebookArchiver, tmp_path: Path
    ) -> None:
        src = tmp_path / "input"
        src.mkdir()
        (src / "file.txt").write_text("x")

        dst = tmp_path / "done" / "sub"
        archiver.archive(src, dst)

        assert dst.exists()
        assert (dst / "file.txt").exists()

    def test_archive_skips_identical_files(
        self, archiver: NotebookArchiver, tmp_path: Path
    ) -> None:
        src = tmp_path / "input"
        src.mkdir()
        (src / "file.txt").write_text("same")

        dst = tmp_path / "done"
        dst.mkdir()
        (dst / "file.txt").write_text("same")

        mtime_before = (dst / "file.txt").stat().st_mtime

        archiver.archive(src, dst)

        # File should not have been overwritten
        mtime_after = (dst / "file.txt").stat().st_mtime
        assert mtime_before == mtime_after

    def test_archive_overwrites_different_files(
        self, archiver: NotebookArchiver, tmp_path: Path
    ) -> None:
        src = tmp_path / "input"
        src.mkdir()
        (src / "file.txt").write_text("new content")

        dst = tmp_path / "done"
        dst.mkdir()
        (dst / "file.txt").write_text("old content")

        archiver.archive(src, dst)

        assert (dst / "file.txt").read_text() == "new content"

    def test_archive_idempotent(
        self, archiver: NotebookArchiver, tmp_path: Path
    ) -> None:
        src = tmp_path / "input"
        src.mkdir()
        (src / "file.txt").write_text("content")

        dst = tmp_path / "done"

        archiver.archive(src, dst)
        archiver.archive(src, dst)

        assert (dst / "file.txt").read_text() == "content"

    def test_archive_input_not_found(
        self, archiver: NotebookArchiver, tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError):
            archiver.archive(tmp_path / "nonexistent", tmp_path / "done")

    def test_archive_copies_binary_files(
        self, archiver: NotebookArchiver, tmp_path: Path
    ) -> None:
        src = tmp_path / "input"
        src.mkdir()
        (src / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")

        dst = tmp_path / "done"
        archiver.archive(src, dst)

        assert (dst / "image.png").read_bytes() == b"\x89PNG\r\n\x1a\n"
