# Directives — notebook-processor

## *Last updated by PM layer: 2026-02-20*

### Context

W9 mid-term notebook successfully ingested and processed (HTML produced). The pipeline works end-to-end with StubSolver. Two bugfixes merged to develop (kernel crash #1, unit tests #2). 241 tests pass.

Three new phases are planned. Each should be implemented as a `feature/*` branch off `develop`, per D-012 (Git Flow lite).

### Priorities

1. **P4a — LLM Asset Analysis** (feature/llm-asset-analysis)
   - Create `src/notebook_processor/ingestion/asset_analyzer.py`
   - LiteLLM wrapper for ingestion context (separate from Solver ABC — Decision D-013)
   - For each Asset in manifest: send file sample (first 50 lines for CSV, structure for JSON, metadata for images) + notebook context to LLM
   - Classify role: `assignment_data`, `reference`, `sample_output`, `configuration`, `unknown`
   - Populate `Asset.description` field from LLM response
   - Activate `InstructionImprover` stub with real LLM analysis
   - Add `Asset.role` field to models.py (new enum `AssetRole`)
   - Update `PackageIngestor.ingest()` to call `AssetAnalyzer` after inventory
   - Tests: mock LLM responses with fixture data

2. **P4b — Advanced Charset Resolution** (feature/charset-resolution)
   - Enhance `data_repair.py` with multi-strategy detection:
     - Primary: charset_normalizer (current)
     - Secondary: byte-level BOM check (UTF-8 BOM, UTF-16 LE/BE)
     - Tertiary: content heuristics (smart quotes → Windows-1252, ñ → Latin-1)
   - New: `CharsetReport` model — per-file analysis with confidence, problematic character inventory
   - New: Notebook code patcher — AST-based detection of `pd.read_csv()` calls → inject `encoding=` parameter (Decision D-014)
   - Add `Asset.charset_analysis` field to models.py
   - Preserve original cell source in metadata before patching
   - Tests: fixtures with known encoding issues

3. **P4c — Auto-Fix Execution Loop** (feature/auto-fix-loop)
   - New: `src/notebook_processor/error_handler.py`
   - Error classifier: parse `PapermillExecutionError` into categories:
     - `ImportError` → add missing import to cell
     - `FileNotFoundError` → fix file path using manifest asset paths
     - `UnicodeDecodeError` → apply charset fix from P4b
     - `NameError` → check previous cells for missing definitions
     - Other → LLM fallback (Decision D-015)
   - Pluggable fix strategy chain (deterministic first, LLM last)
   - Cell patcher: modify cell source, store original in `cell.metadata["original_source"]`
   - Execution loop in `executor.py` or new `auto_executor.py`:
     ```
     for attempt in range(max_retries):
         try: execute(notebook) → break
         except ExecutionError: classify → fix → continue
     ```
   - Execution report: JSON log of each iteration (error, fix, outcome)
   - CLI: `--max-retries N` flag on `process` and `run` commands
   - Tests: simulated PapermillExecutionError with various categories

### Constraints

- Work on `develop` branch; create `feature/*` branches per phase
- Run `uv run mypy src/` and `uv run pytest -v --timeout=30` after each step
- Conventional Commits for all commit messages
- All LLM calls must be mockable (inject client or use environment variable)
- All papermill/nbconvert calls must be mocked in tests
- Never write files outside the repo root
- Never write files into `../project-management/`
- Update `journal.md` after each phase completion

### Decisions

- D-013: LLM in ingestion uses separate LiteLLM wrapper, NOT the Solver ABC
- D-014: AST-level pd.read_csv() patching, preserve original in cell metadata
- D-015: Pluggable error-handler chain (deterministic first, LLM fallback), max 5 retries default

### Answers to Blockers

- **Kernel crash**: Resolved (Bug #1, _ensure_kernel in executor.py)
- **StubSolver hardcoded in CLI**: Will be addressed when ClaudeSolver is implemented (P5). For now P4c auto-fix handles execution errors post-stub.
