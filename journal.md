# Journal — notebook-processor

### 2026-02-19T00:00:00Z — Initial Assessment: PLAN.md Steps
**Status**: Assessment complete
**Changes**: journal.md created
**Findings**:
- All pre-existing ingestion code (CLAUDE.md Tasks 2.13–2.20) is fully implemented and passing (203 tests, mypy clean)
- PLAN.md Step 1: `project_layout.py` — NOT STARTED (file does not exist)
- PLAN.md Step 2: `models.py` + `pipeline.py` changes — NOT STARTED (`PipelineState.done_path` still `str`, no `run_project`)
- PLAN.md Step 3: `ingestor.py` additions — NOT STARTED (no `ingest_project` or `_archive_originals`)
- PLAN.md Step 4: CLI restructuring — NOT STARTED (no `run`/`validate` commands, old `--input/--output` convention)
- PLAN.md Step 5: Makefile + examples cleanup — NOT STARTED
**Next**: Step 1 — implement `ProjectLayout` + tests

### 2026-02-19T00:01:00Z — Housekeeping: Commit untracked files
**Status**: Complete
**Changes**: Committed CLAUDE.md, directives.md, plan.md, .gitignore, test fixtures
**Next**: Step 1 — implement `ProjectLayout`
**Blockers**: None

### 2026-02-19T00:10:00Z — Steps 1–5: Unified Project Folder Convention
**Status**: Complete
**Changes**:
- NEW: `src/notebook_processor/project_layout.py` — `ProjectLayout` class (root resolution, auto-sequential run naming, loose-file detection)
- NEW: `src/notebook_processor/reembed.py` — re-embed original images into completed notebooks
- NEW: `tests/test_project_layout.py` — 22 tests
- MODIFIED: `src/notebook_processor/models.py` — `PipelineState.done_path` now `str | None`
- MODIFIED: `src/notebook_processor/pipeline.py` — `done_dir=None` skips archive; added `run_project(layout, solver)`
- MODIFIED: `src/notebook_processor/ingestion/ingestor.py` — added `ingest_project(layout)`, `_archive_originals(layout)`
- MODIFIED: `src/notebook_processor/cli.py` — unified FOLDER convention: `ingest`, `process`, `run`, `validate` commands
- MODIFIED: `src/notebook_processor/__init__.py` — export `ProjectLayout`
- MODIFIED: `Makefile` — `PROJECT` variable replaces `INPUT/OUTPUT/DONE`
- MODIFIED: `examples/jhu-demo/` — files moved from `raw/` to project root
- MODIFIED: `tests/test_cli.py`, `tests/test_pipeline.py`, `tests/test_ingestor.py` — updated + new tests
- MODIFIED: `.gitignore` — added `.claude/`, jhu-demo output dirs
**Verification**: 234 tests pass, mypy clean (22 source files)
**Commit**: `feat: implement unified project folder convention` (5c2b0b8)
**Next**: Implementation complete per PLAN.md
**Blockers**: None

### 2026-02-20T10:00:00Z — Bug #1: Executor crashes on stale kernel path
**Status**: Complete
**Branch**: `fix/1-executor-kernel-crash` (from `develop`)
**Issue**: [#1](https://github.com/jeanremacle/notebook-processor/issues/1)
**Root cause**: The registered `python3` Jupyter kernel pointed to a stale `.venv/bin/python3` path from a Dropbox directory. The executor only caught `PapermillExecutionError`, so `FileNotFoundError` from the kernel launcher crashed the entire pipeline.
**Fix**:
- `executor.py`: Added `_ensure_kernel()` — detects stale kernel specs and re-registers using current `sys.executable`
- `executor.py`: Broadened exception handling to catch all execution errors, not just `PapermillExecutionError`
- Added 2 new unit tests for kernel launch failure and `_ensure_kernel` invocation
**Changes**:
- MODIFIED: `src/notebook_processor/executor.py`
- MODIFIED: `tests/test_executor.py`
- NEW: `CHANGELOG.md`
- MODIFIED: `src/notebook_processor/__init__.py` — `__version__ = "0.1.1"`
- MODIFIED: `pyproject.toml` — dynamic versioning via hatchling
- NEW: `examples/jhu-week9-midterm-project/` — real-world test fixture
**Verification**: 236 tests pass, mypy clean. Real-world notebook runs successfully (kernel auto-fixed, pipeline completes with expected cell-level errors from StubSolver).
**Time to completion**: ~30 minutes
**Next**: Merge into `develop`
**Blockers**: None
