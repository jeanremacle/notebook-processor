# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-02-20

### Fixed

- Executor crashes with `FileNotFoundError` when the registered `python3`
  Jupyter kernel points to a stale `.venv` path ([#1](https://github.com/jeanremacle/notebook-processor/issues/1))
- Executor now catches all execution exceptions (not just `PapermillExecutionError`)
  and wraps them as `ExecutionError` so the pipeline can continue gracefully

### Added

- `_ensure_kernel()` auto-detects stale kernel specs and re-registers the
  `python3` kernel using the current environment's `sys.executable`
- Release infrastructure: `__version__` in `__init__.py`, dynamic versioning
  via hatchling, CHANGELOG.md
- Real-world test fixture: `examples/jhu-week9-midterm-project/`

## [0.1.0] - 2026-02-19

### Added

- Core pipeline: parse, solve, build, execute, export, archive
- Package ingestion module: inventory scanner, data repair (encoding detection),
  notebook preprocessor (image extraction, TODO marker detection, dependency detection),
  instruction improver (stub), manifest generator
- Unified project folder convention (`ProjectLayout`) with auto-sequential run naming
- CLI commands: `ingest`, `process`, `run`, `validate`, `parse`, `execute`, `export`
- Image re-embedding for validated output (`reembed.py`)
- `StubSolver` and `ManualSolver` implementations
- Benchmark framework integration bridge
- Full test suite (234 tests)

[Unreleased]: https://github.com/jeanremacle/notebook-processor/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/jeanremacle/notebook-processor/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jeanremacle/notebook-processor/releases/tag/v0.1.0
