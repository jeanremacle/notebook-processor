# Directives — notebook-processor

## *Last updated by PM layer: 2026-02-19*

### Priorities

1. Read `PLAN.md` for the full implementation plan (Unified Project Folder Convention)
2. Read `CLAUDE.md` for all project context and conventions
3. Resume implementation following the Implementation Order in `PLAN.md` (steps 1–7)

### Decisions

- The previous Claude Code session was lost (corrupted image in conversation context). Start fresh, but check existing source files to avoid redoing completed work.
- If files from a step already exist and pass tests, mark that step as complete in `journal.md` and move to the next.

### Constraints

- Run `uv run mypy src/` and `uv run pytest -v --timeout=30` after each step before journaling completion
- Conventional Commits for all commit messages
- Never write files outside the repo root
- Never write files into `../project-management/`
- All papermill/nbconvert calls must be mocked in tests (no real kernel launches)
- Single commit at the end per PLAN.md step 7

### Answers to Blockers

*No blockers raised yet.*
