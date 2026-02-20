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
**Status**: Fixed, merged into `develop`, v0.1.1
**Issue**: [#1](https://github.com/jeanremacle/notebook-processor/issues/1)
**Summary**: Stale `python3` Jupyter kernel spec crashed the pipeline. Fixed by auto-detecting and re-registering the kernel, plus broadening exception handling in the executor. 236 tests pass.
**Branch**: `fix/1-executor-kernel-crash`
**Blockers**: None

### 2026-02-20T11:00:00Z — Issue #2: Add unit tests for _ensure_kernel
**Status**: Complete
**Issue**: [#2](https://github.com/jeanremacle/notebook-processor/issues/2)
**Summary**: Added 5 unit tests for `_ensure_kernel` stale-kernel detection logic (bug #1 fix). Previous tests only monkeypatched at the papermill level. Committed directly to `develop` without a feature branch. 241 tests pass.
**Commit**: `test: add unit tests for _ensure_kernel stale-kernel detection` (edeef77)
**Blockers**: None
