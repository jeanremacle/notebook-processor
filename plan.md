# Plan: Unified Project Folder Convention

## Context

Currently `ingest` and `process` are disconnected commands with separate folder arguments. The user wants a single project folder convention where:

- You pass one folder (the project root)
- Originals get moved to `root/input/`
- Ingestion output goes to `root/ingested/`
- Processing output goes to `root/output/{run-name}/`
- `done/` is eliminated — `input/` serves as the archive

## Target Folder Structure

```text
my-assignments/
└── project1/              ← project root
    ├── input/             ← originals moved here
    ├── ingested/          ← normalized package
    └── output/
        ├── run-001/       ← auto-sequential
        └── my-custom/     ← user-provided --name
```

## Files to Create/Modify

### 1. NEW: `src/notebook_processor/project_layout.py`

`ProjectLayout` class — single source of truth for path resolution:

- `__init__(path)`: if path name is `"input"`, root = parent; otherwise root = path
- Properties: `.root`, `.input_dir`, `.ingested_dir`, `.output_dir`
- `run_dir(name=None)` → `output/{name}` or `output/run-NNN` (auto-sequential)
- `_next_run_name()` → scans `output/` for `run-\d{3}` dirs, returns next
- `has_loose_files()` → True if root has files/dirs outside `input/ingested/output`
- `input_already_populated()` → True if `input/` has any content
- `ensure_dirs()` → creates all three subdirs

### 2. MODIFY: `src/notebook_processor/models.py`

- `PipelineState.done_path`: change from `str` to `str | None = None`

### 3. MODIFY: `src/notebook_processor/pipeline.py`

- `run()`: make `done_dir` parameter `str | Path | None`, skip archive step when `None`
- `_load_or_create_state()`: accept `done_path: Path | None`
- NEW `run_project(layout, solver, *, run_name=None)`: convention-aware wrapper that calls `run(ingested_dir, run_dir, done_dir=None, solver)`

### 4. MODIFY: `src/notebook_processor/ingestion/ingestor.py`

- NEW `ingest_project(layout, *, force=False)`:
  - Calls `_archive_originals()` to move loose files into `input/`
  - If `ingested/manifest.json` exists and not force: return cached manifest
  - If force: clear `ingested/` first
  - Delegates to existing `ingest(input_dir, ingested_dir)`
- NEW `_archive_originals(layout, *, force=False)`:
  - If no loose files: no-op
  - If `input/` populated AND loose files exist AND not force: raise `FileExistsError`
  - Otherwise: `shutil.move()` each loose file/dir into `input/`

### 5. MODIFY: `src/notebook_processor/cli.py`

Four main commands, all take `FOLDER` (project root or its `input/` subfolder):

| Command  | Args                    | Behavior                                                   |
| -------- | ----------------------  | ---------------------------------------------------------- |
| ingest   | FOLDER, --force         | Move originals → `input/`, run ingestion → `ingested/`     |
| process  | FOLDER, --name          | Read from `ingested/`, write to `output/{name}`            |
| run      | FOLDER, --name, --force | ingest then process                                        |
| validate | FOLDER, --name          | Re-embed original images into output notebook, export HTML |

**validate command detail:**

- Reads the completed notebook from `output/{name}/`
- Reads the original notebook from `input/` (which has all base64 images intact)
- Re-embeds the original images into the completed notebook
- Exports to HTML → `output/{name}/validated.html`
- This gives the final deliverable with all original images + completed answers

Preserve utility commands unchanged: `parse`, `execute`, `export`.

### 5b. NEW: Image re-embedding logic

A helper (in a new module or in `pipeline.py`) that:

- Reads the original notebook from `input/` and extracts image data from cell outputs
- Reads the completed notebook from `output/{name}/`
- Injects the original image outputs back into matching cells
- Writes the merged notebook, then exports to HTML

### 5c. Future: Image triage during ingestion (Phase 4, NOT this PR)

During ingestion, the preprocessor currently extracts ALL base64 images. In a future phase, LLM vision will classify images as:

- **Instructional** (diagrams, examples) → keep with descriptive text in cleaned notebook
- **Sample output** (disposable) → remove as today

This is stubbed for now — all images are extracted identically.

### 6. MODIFY: `Makefile`

- Replace `INPUT/OUTPUT/DONE` vars with `PROJECT ?= examples/jhu-demo`
- `make ingest` → `ingest $(PROJECT)`
- `make process` → `process $(PROJECT)`
- `make run` → `run $(PROJECT)`

### 7. MODIFY: `examples/jhu-demo/`

- Move files from `raw/` up to project root (so they're "loose files")
- Remove `raw/` subdirectory

### 8. MODIFY: `src/notebook_processor/__init__.py`

- Export `ProjectLayout`

## Test Strategy

### NEW: `tests/test_project_layout.py`

- Root resolution from project dir vs `input/` subdir
- Path properties
- Auto-sequential naming (empty, existing runs, gaps)
- Custom run name
- `has_loose_files()` with various layouts
- `input_already_populated()`

### MODIFY: `tests/test_cli.py`

- Update `test_ingest_command` for new single-arg convention
- Update `test_process_command` for new convention
- Add `test_run_command` (end-to-end)
- Add `test_process_sequential_naming`
- Add `test_validate_command` (re-embeds images, produces HTML)
- Keep `test_parse_command`, `test_execute_command`, `test_export_command` unchanged

### MODIFY: `tests/test_pipeline.py`

- Existing tests: pass `done_dir` as before (backwards compatible)
- Add `test_pipeline_no_done_dir` (archive step skipped)
- Add `test_run_project` via `ProjectLayout`

### MODIFY: `tests/test_ingestor.py`

- Existing tests preserved (low-level API unchanged)
- Add `test_ingest_project` (loose files → `input/` → `ingested/`)
- Add `test_ingest_project_skip_cached`
- Add `test_ingest_project_force`
- Add `test_archive_originals_conflict`

## Implementation Order

1. `project_layout.py` + `test_project_layout.py` — foundation, no existing code touched
2. `models.py` + `pipeline.py` + `test_pipeline.py` — backwards-compatible changes
3. `ingestor.py` + `test_ingestor.py` — backwards-compatible additions
4. `cli.py` + `test_cli.py` — CLI restructuring
5. `Makefile` + `examples/` + `__init__.py` — cleanup
6. Full `mypy src/` + `pytest --timeout=30` verification
7. Single commit

## Verification

```bash
uv run mypy src/                    # must pass clean
uv run pytest -v --timeout=30       # all tests pass

# Manual end-to-end:
uv run python -m notebook_processor run examples/jhu-demo
# Should produce: examples/jhu-demo/{input,ingested,output/run-001}/

uv run python -m notebook_processor validate examples/jhu-demo --name run-001
# Should produce: examples/jhu-demo/output/run-001/validated.html
```
