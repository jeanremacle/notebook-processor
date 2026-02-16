# Notebook Processor

Automated pipeline for processing Jupyter Notebook assignments — parse, solve, execute, export, archive.

## Quick Start

```bash
# Install dependencies
make setup

# Run tests
make test

# Process a notebook
make process INPUT=path/to/input/
```

## Pipeline Steps

1. **Parse** — Read `.ipynb`, detect TODO cells, load companion instructions and images
2. **Solve** — Complete TODO cells (code and markdown). Pluggable solver interface.
3. **Build** — Reconstruct valid `.ipynb` with completed cells
4. **Execute** — Run the notebook via papermill, capture outputs
5. **Export** — Convert executed notebook to self-contained HTML
6. **Archive** — Copy original input files to `done/`

## Directory Convention

```text
input/                      # Source files
├── assignment.ipynb        # Notebook with TODO cells
├── instructions.md         # Optional companion instructions
└── images/                 # Optional reference images

output/                     # Generated deliverables
├── assignment_completed.ipynb
├── assignment_completed.html   # ← deliverable
└── comparison_report.md        # If benchmark enabled

done/                       # Archived originals
└── (exact copy of input/)
```

## Solver Interface

The pipeline uses a pluggable solver:

- `StubSolver` — Returns placeholder text (for testing)
- `ManualSolver` — Interactive stdin prompts
- Future: `ClaudeSolver` — API-based completion via Anthropic

## Dependencies

- [benchmark-framework](https://github.com/jeanremacle/benchmark-framework) — Optional benchmark integration

## License

MIT
