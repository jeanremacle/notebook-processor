"""Script to create the sample_assignment.ipynb test fixture."""

from pathlib import Path

import nbformat

fixtures_dir = Path(__file__).parent / "fixtures"


def create_sample_assignment() -> None:
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.metadata["language_info"] = {
        "name": "python",
        "version": "3.11.0",
    }

    # Cell 0: Markdown intro (ORIGINAL)
    nb.cells.append(
        nbformat.v4.new_markdown_cell(
            "# Sample Assignment\n\nComplete the cells below."
        )
    )

    # Cell 1: TODO code cell with NotImplementedError
    nb.cells.append(
        nbformat.v4.new_code_cell(
            "# TODO: Implement factorial\n"
            "def factorial(n):\n"
            '    raise NotImplementedError("Complete this")'
        )
    )

    # Cell 2: TODO code cell with YOUR CODE HERE
    nb.cells.append(
        nbformat.v4.new_code_cell("def add(a, b):\n    # YOUR CODE HERE\n    pass")
    )

    # Cell 3: Pre-filled code cell (ORIGINAL)
    nb.cells.append(
        nbformat.v4.new_code_cell("# Verification\nassert True\nprint('OK')")
    )

    # Cell 4: TODO markdown cell
    nb.cells.append(
        nbformat.v4.new_markdown_cell(
            "## Question\n\nExplain your approach.\n\n**Your answer here:**"
        )
    )

    out_path = fixtures_dir / "sample_assignment.ipynb"
    nbformat.write(nb, str(out_path))
    print(f"Created {out_path}")


if __name__ == "__main__":
    create_sample_assignment()
