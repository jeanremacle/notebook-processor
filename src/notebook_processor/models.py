"""Pydantic models for notebook processing."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Core pipeline models
# ---------------------------------------------------------------------------


class CellType(StrEnum):
    """Notebook cell types."""

    CODE = "code"
    MARKDOWN = "markdown"
    RAW = "raw"


class CellStatus(StrEnum):
    """Processing status of a notebook cell."""

    ORIGINAL = "original"
    TODO_CODE = "todo_code"
    TODO_MARKDOWN = "todo_markdown"
    COMPLETED = "completed"
    ADDED = "added"


class NotebookCell(BaseModel):
    """Represents a single notebook cell with processing metadata."""

    index: int
    cell_type: CellType
    source: str
    status: CellStatus = CellStatus.ORIGINAL
    original_source: str | None = None
    outputs: list[dict[str, object]] | None = None


class InstructionFile(BaseModel):
    """Parsed companion instruction file."""

    path: str
    content: str
    images: list[str] = []


class NotebookContent(BaseModel):
    """Complete parsed notebook with metadata."""

    path: str
    cells: list[NotebookCell]
    metadata: dict[str, object]
    instructions: InstructionFile | None = None
    kernel_spec: str | None = None


class PipelineState(BaseModel):
    """Tracks pipeline progress for resume capability."""

    input_path: str
    output_path: str
    done_path: str | None = None
    current_step: str
    completed_steps: list[str] = []
    errors: list[str] = []


# ---------------------------------------------------------------------------
# Package ingestion models
# ---------------------------------------------------------------------------


class AssetType(StrEnum):
    """Type of file within a notebook package."""

    NOTEBOOK = "notebook"
    DATA = "data"
    IMAGE = "image"
    INSTRUCTIONS = "instructions"
    SUPPLEMENT = "supplement"


class DataQualityIssue(StrEnum):
    """Categories of data quality issues found during ingestion."""

    ENCODING = "encoding"
    LINE_ENDINGS = "line_endings"
    MISSING_VALUES = "missing_values"
    INCONSISTENT_TYPES = "inconsistent_types"


class DataSchema(BaseModel):
    """Schema summary for a data file — never the full content."""

    columns: list[str]
    dtypes: dict[str, str] = {}
    row_count: int
    sample_head: list[dict[str, object]] = []
    sample_tail: list[dict[str, object]] = []
    null_counts: dict[str, int] = {}


class DataTransformation(BaseModel):
    """Record of a single data transformation applied during ingestion."""

    original_path: str
    issue: DataQualityIssue
    action: str
    details: str
    records_affected: int = 0
    confidence: float = 1.0
    backup_path: str | None = None


class ExtractedImage(BaseModel):
    """An image extracted from an inline base64 notebook cell."""

    cell_index: int
    original_size_bytes: int
    extracted_path: str
    description: str | None = None
    purpose: str = "sample_output"


class Asset(BaseModel):
    """A single file within the notebook package."""

    path: str
    type: AssetType
    format: str
    size_bytes: int
    schema_info: DataSchema | None = None
    contents: list[str] | None = None
    description: str | None = None
    transformations: list[DataTransformation] = []
    extracted_images: list[ExtractedImage] = []


class TodoMarker(BaseModel):
    """A detected TODO cell in the notebook."""

    cell_index: int
    cell_type: CellType
    marker_pattern: str
    variable_name: str | None = None
    task_id: str | None = None
    context: str = ""


class NotebookAnalysis(BaseModel):
    """Analysis results from notebook preprocessing."""

    total_cells: int
    cell_type_counts: dict[str, int]
    todo_markers: list[TodoMarker]
    embedded_images_count: int
    embedded_images_total_bytes: int
    dependencies: list[str] = []
    api_dependencies: list[str] = []
    hardcoded_paths: list[str] = []
    kernel_spec: str | None = None


class InstructionImprovement(BaseModel):
    """Record of an instruction that was clarified or split."""

    original_text: str
    improved_text: str
    sub_steps: list[str] = []
    rationale: str


class PackageMetadata(BaseModel):
    """Top-level package metadata."""

    id: str
    name: str
    course: str = ""
    created_at: str
    status: str = "pending"


class NotebookMetadata(BaseModel):
    """Notebook-specific metadata."""

    filename: str
    original_filename: str
    kernel: str = "python3"
    requires_gpu: bool = False
    analysis: NotebookAnalysis | None = None


class LlmConfig(BaseModel):
    """LLM model configuration for delivery vs optimization."""

    delivery: str = ""
    default: str = ""


class BenchmarkConfig(BaseModel):
    """Benchmark configuration."""

    enabled: bool = False
    iterations: list[str] = []


class PackageManifest(BaseModel):
    """Complete manifest for a notebook package."""

    package: PackageMetadata
    notebook: NotebookMetadata
    assets: list[Asset]
    instruction_improvements: list[InstructionImprovement] = []
    llm_config: LlmConfig = LlmConfig()
    benchmark: BenchmarkConfig = BenchmarkConfig()
    outputs: list[str] = []
