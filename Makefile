.PHONY: setup test lint clean process format

INPUT ?= examples/demo/input
OUTPUT ?= examples/demo/output
DONE ?= examples/demo/done

setup:
	uv sync --all-extras

test:
	uv run pytest -v --cov=notebook_processor

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src/

format:
	uv run ruff format .
	uv run ruff check --fix .

clean:
	rm -rf .venv __pycache__ .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

process:
	uv run python -m notebook_processor process $(INPUT) --output $(OUTPUT) --done $(DONE)
