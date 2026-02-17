"""Tests for ingestion Pydantic models and TransformationLogger."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from notebook_processor.ingestion.transformations import TransformationLogger
from notebook_processor.models import (
    Asset,
    AssetType,
    BenchmarkConfig,
    CellType,
    DataQualityIssue,
    DataSchema,
    DataTransformation,
    ExtractedImage,
    InstructionImprovement,
    LlmConfig,
    NotebookAnalysis,
    NotebookMetadata,
    PackageManifest,
    PackageMetadata,
    TodoMarker,
)

# ---------------------------------------------------------------------------
# AssetType / DataQualityIssue enums
# ---------------------------------------------------------------------------


class TestAssetType:
    def test_values(self) -> None:
        assert AssetType.NOTEBOOK == "notebook"
        assert AssetType.DATA == "data"
        assert AssetType.IMAGE == "image"
        assert AssetType.INSTRUCTIONS == "instructions"
        assert AssetType.SUPPLEMENT == "supplement"


class TestDataQualityIssue:
    def test_values(self) -> None:
        assert DataQualityIssue.ENCODING == "encoding"
        assert DataQualityIssue.LINE_ENDINGS == "line_endings"
        assert DataQualityIssue.MISSING_VALUES == "missing_values"
        assert DataQualityIssue.INCONSISTENT_TYPES == "inconsistent_types"


# ---------------------------------------------------------------------------
# DataSchema
# ---------------------------------------------------------------------------


class TestDataSchema:
    def test_minimal(self) -> None:
        schema = DataSchema(columns=["a", "b"], row_count=10)
        assert schema.columns == ["a", "b"]
        assert schema.row_count == 10
        assert schema.dtypes == {}
        assert schema.sample_head == []
        assert schema.null_counts == {}

    def test_full(self) -> None:
        schema = DataSchema(
            columns=["id", "name", "score"],
            dtypes={"id": "int64", "name": "object", "score": "float64"},
            row_count=100,
            sample_head=[{"id": 1, "name": "Alice", "score": 95.5}],
            sample_tail=[{"id": 100, "name": "Zoe", "score": 72.0}],
            null_counts={"score": 3},
        )
        assert len(schema.sample_head) == 1
        assert schema.null_counts["score"] == 3

    def test_serialization_roundtrip(self) -> None:
        schema = DataSchema(
            columns=["x"], row_count=5, dtypes={"x": "int64"}
        )
        restored = DataSchema.model_validate(schema.model_dump())
        assert restored == schema


# ---------------------------------------------------------------------------
# DataTransformation
# ---------------------------------------------------------------------------


class TestDataTransformation:
    def test_minimal(self) -> None:
        t = DataTransformation(
            original_path="data.csv",
            issue=DataQualityIssue.ENCODING,
            action="Converted Windows-1252 to UTF-8",
            details="Detected Windows-1252 encoding",
        )
        assert t.records_affected == 0
        assert t.confidence == 1.0
        assert t.backup_path is None

    def test_full(self) -> None:
        t = DataTransformation(
            original_path="data.csv",
            issue=DataQualityIssue.ENCODING,
            action="Converted Windows-1252 to UTF-8",
            details="5 smart quote characters replaced",
            records_affected=5,
            confidence=0.95,
            backup_path="data.csv.orig",
        )
        assert t.records_affected == 5
        assert t.confidence == 0.95
        assert t.backup_path == "data.csv.orig"

    def test_invalid_issue(self) -> None:
        with pytest.raises(ValidationError):
            DataTransformation(
                original_path="data.csv",
                issue="bad_issue",  # type: ignore[arg-type]
                action="test",
                details="test",
            )


# ---------------------------------------------------------------------------
# ExtractedImage
# ---------------------------------------------------------------------------


class TestExtractedImage:
    def test_defaults(self) -> None:
        img = ExtractedImage(
            cell_index=5,
            original_size_bytes=12345,
            extracted_path="images/sample_output_cell5.png",
        )
        assert img.description is None
        assert img.purpose == "sample_output"

    def test_with_description(self) -> None:
        img = ExtractedImage(
            cell_index=5,
            original_size_bytes=12345,
            extracted_path="images/sample_output_cell5.png",
            description="Bar chart of results",
            purpose="diagram",
        )
        assert img.description == "Bar chart of results"
        assert img.purpose == "diagram"


# ---------------------------------------------------------------------------
# Asset
# ---------------------------------------------------------------------------


class TestAsset:
    def test_minimal(self) -> None:
        asset = Asset(
            path="notebook.ipynb",
            type=AssetType.NOTEBOOK,
            format="ipynb",
            size_bytes=1024,
        )
        assert asset.schema_info is None
        assert asset.contents is None
        assert asset.transformations == []
        assert asset.extracted_images == []

    def test_data_asset_with_schema(self) -> None:
        schema = DataSchema(columns=["a"], row_count=10)
        asset = Asset(
            path="data/emails.csv",
            type=AssetType.DATA,
            format="csv",
            size_bytes=5000,
            schema_info=schema,
        )
        assert asset.schema_info is not None
        assert asset.schema_info.row_count == 10

    def test_serialization_roundtrip(self) -> None:
        asset = Asset(
            path="test.csv",
            type=AssetType.DATA,
            format="csv",
            size_bytes=100,
            transformations=[
                DataTransformation(
                    original_path="test.csv",
                    issue=DataQualityIssue.ENCODING,
                    action="convert",
                    details="utf-8",
                )
            ],
        )
        restored = Asset.model_validate_json(asset.model_dump_json())
        assert restored == asset


# ---------------------------------------------------------------------------
# TodoMarker
# ---------------------------------------------------------------------------


class TestTodoMarker:
    def test_minimal(self) -> None:
        marker = TodoMarker(
            cell_index=3,
            cell_type=CellType.CODE,
            marker_pattern=r"<-- YOUR SYSTEM PROMPT GOES HERE -->",
        )
        assert marker.variable_name is None
        assert marker.task_id is None
        assert marker.context == ""

    def test_full(self) -> None:
        marker = TodoMarker(
            cell_index=3,
            cell_type=CellType.CODE,
            marker_pattern=r"<-- YOUR SYSTEM PROMPT GOES HERE -->",
            variable_name="system_prompt",
            task_id="1A",
            context='system_prompt = """\n...\n"""',
        )
        assert marker.variable_name == "system_prompt"
        assert marker.task_id == "1A"


# ---------------------------------------------------------------------------
# NotebookAnalysis
# ---------------------------------------------------------------------------


class TestNotebookAnalysis:
    def test_minimal(self) -> None:
        analysis = NotebookAnalysis(
            total_cells=10,
            cell_type_counts={"code": 6, "markdown": 4},
            todo_markers=[],
            embedded_images_count=0,
            embedded_images_total_bytes=0,
        )
        assert analysis.total_cells == 10
        assert analysis.dependencies == []
        assert analysis.api_dependencies == []
        assert analysis.hardcoded_paths == []
        assert analysis.kernel_spec is None

    def test_with_markers_and_deps(self) -> None:
        marker = TodoMarker(
            cell_index=3,
            cell_type=CellType.CODE,
            marker_pattern="# TODO",
        )
        analysis = NotebookAnalysis(
            total_cells=10,
            cell_type_counts={"code": 6, "markdown": 4},
            todo_markers=[marker],
            embedded_images_count=2,
            embedded_images_total_bytes=50000,
            dependencies=["pandas", "openai"],
            api_dependencies=["openai"],
            hardcoded_paths=["your_file_location"],
            kernel_spec="python3",
        )
        assert len(analysis.todo_markers) == 1
        assert analysis.dependencies == ["pandas", "openai"]


# ---------------------------------------------------------------------------
# InstructionImprovement
# ---------------------------------------------------------------------------


class TestInstructionImprovement:
    def test_minimal(self) -> None:
        imp = InstructionImprovement(
            original_text="Do the thing",
            improved_text="Complete the analysis",
            rationale="Original was vague",
        )
        assert imp.sub_steps == []

    def test_with_sub_steps(self) -> None:
        imp = InstructionImprovement(
            original_text="Do the thing",
            improved_text="Complete the analysis",
            sub_steps=["Load data", "Compute metrics", "Plot results"],
            rationale="Decomposed into measurable steps",
        )
        assert len(imp.sub_steps) == 3


# ---------------------------------------------------------------------------
# PackageMetadata / NotebookMetadata / LlmConfig / BenchmarkConfig
# ---------------------------------------------------------------------------


class TestPackageMetadata:
    def test_minimal(self) -> None:
        meta = PackageMetadata(
            id="w9-email",
            name="Email Prioritization",
            created_at="2025-02-14T10:00:00Z",
        )
        assert meta.course == ""
        assert meta.status == "pending"

    def test_full(self) -> None:
        meta = PackageMetadata(
            id="w9-email",
            name="Email Prioritization",
            course="EN.705.603",
            created_at="2025-02-14T10:00:00Z",
            status="done",
        )
        assert meta.course == "EN.705.603"


class TestNotebookMetadata:
    def test_defaults(self) -> None:
        nb = NotebookMetadata(
            filename="notebook.ipynb",
            original_filename="Week9_Assignment.ipynb",
        )
        assert nb.kernel == "python3"
        assert nb.requires_gpu is False
        assert nb.analysis is None


class TestLlmConfig:
    def test_defaults(self) -> None:
        cfg = LlmConfig()
        assert cfg.delivery == ""
        assert cfg.default == ""


class TestBenchmarkConfig:
    def test_defaults(self) -> None:
        cfg = BenchmarkConfig()
        assert cfg.enabled is False
        assert cfg.iterations == []


# ---------------------------------------------------------------------------
# PackageManifest
# ---------------------------------------------------------------------------


class TestPackageManifest:
    def test_minimal(self) -> None:
        manifest = PackageManifest(
            package=PackageMetadata(
                id="test",
                name="Test Package",
                created_at="2025-01-01T00:00:00Z",
            ),
            notebook=NotebookMetadata(
                filename="notebook.ipynb",
                original_filename="orig.ipynb",
            ),
            assets=[],
        )
        assert manifest.instruction_improvements == []
        assert manifest.llm_config == LlmConfig()
        assert manifest.benchmark == BenchmarkConfig()
        assert manifest.outputs == []

    def test_full_roundtrip(self) -> None:
        manifest = PackageManifest(
            package=PackageMetadata(
                id="w9",
                name="Week 9",
                created_at="2025-02-14T10:00:00Z",
            ),
            notebook=NotebookMetadata(
                filename="notebook.ipynb",
                original_filename="Week9.ipynb",
            ),
            assets=[
                Asset(
                    path="data/emails.csv",
                    type=AssetType.DATA,
                    format="csv",
                    size_bytes=5000,
                )
            ],
            llm_config=LlmConfig(delivery="gpt-4o"),
            benchmark=BenchmarkConfig(enabled=True, iterations=["v1"]),
            outputs=["output/notebook_completed.html"],
        )
        json_str = manifest.model_dump_json()
        restored = PackageManifest.model_validate_json(json_str)
        assert restored == manifest
        assert restored.assets[0].type == AssetType.DATA


# ---------------------------------------------------------------------------
# TransformationLogger
# ---------------------------------------------------------------------------


class TestTransformationLogger:
    @pytest.fixture
    def logger(self) -> TransformationLogger:
        return TransformationLogger()

    @pytest.fixture
    def sample_transformation(self) -> DataTransformation:
        return DataTransformation(
            original_path="data.csv",
            issue=DataQualityIssue.ENCODING,
            action="Converted Windows-1252 to UTF-8",
            details="Detected Windows-1252 encoding with smart quotes",
            records_affected=5,
            backup_path="data.csv.orig",
        )

    def test_empty_logger(self, logger: TransformationLogger) -> None:
        assert logger.entries == []
        assert logger.get_summary() == "No transformations applied."

    def test_log_entry(
        self,
        logger: TransformationLogger,
        sample_transformation: DataTransformation,
    ) -> None:
        logger.log(sample_transformation)
        assert len(logger.entries) == 1
        assert logger.entries[0] == sample_transformation

    def test_entries_returns_copy(
        self,
        logger: TransformationLogger,
        sample_transformation: DataTransformation,
    ) -> None:
        logger.log(sample_transformation)
        entries = logger.entries
        entries.clear()
        assert len(logger.entries) == 1

    def test_multiple_entries(
        self, logger: TransformationLogger
    ) -> None:
        logger.log(
            DataTransformation(
                original_path="a.csv",
                issue=DataQualityIssue.ENCODING,
                action="convert",
                details="utf-8",
            )
        )
        logger.log(
            DataTransformation(
                original_path="b.csv",
                issue=DataQualityIssue.LINE_ENDINGS,
                action="normalize",
                details="CRLF to LF",
            )
        )
        assert len(logger.entries) == 2

    def test_get_summary_single(
        self,
        logger: TransformationLogger,
        sample_transformation: DataTransformation,
    ) -> None:
        logger.log(sample_transformation)
        summary = logger.get_summary()
        assert "1 transformation(s)" in summary
        assert "encoding" in summary

    def test_get_summary_multiple(
        self, logger: TransformationLogger
    ) -> None:
        logger.log(
            DataTransformation(
                original_path="a.csv",
                issue=DataQualityIssue.ENCODING,
                action="convert",
                details="utf-8",
            )
        )
        logger.log(
            DataTransformation(
                original_path="a.csv",
                issue=DataQualityIssue.ENCODING,
                action="replace",
                details="smart quotes",
            )
        )
        logger.log(
            DataTransformation(
                original_path="a.csv",
                issue=DataQualityIssue.LINE_ENDINGS,
                action="normalize",
                details="CRLF",
            )
        )
        summary = logger.get_summary()
        assert "3 transformation(s)" in summary
        assert "encoding" in summary
        assert "line_endings" in summary

    def test_save(
        self,
        tmp_path: Path,
        logger: TransformationLogger,
        sample_transformation: DataTransformation,
    ) -> None:
        logger.log(sample_transformation)
        log_path = tmp_path / "transformations.log"
        logger.save(log_path)

        content = log_path.read_text(encoding="utf-8")
        assert "[1] ENCODING" in content
        assert "Converted Windows-1252 to UTF-8" in content
        assert "data.csv" in content
        assert "Records affected: 5" in content
        assert "Backup: data.csv.orig" in content

    def test_save_with_low_confidence(
        self, tmp_path: Path, logger: TransformationLogger
    ) -> None:
        logger.log(
            DataTransformation(
                original_path="data.csv",
                issue=DataQualityIssue.ENCODING,
                action="convert",
                details="heuristic",
                confidence=0.85,
            )
        )
        log_path = tmp_path / "transformations.log"
        logger.save(log_path)

        content = log_path.read_text(encoding="utf-8")
        assert "Confidence: 85%" in content

    def test_save_empty(
        self, tmp_path: Path, logger: TransformationLogger
    ) -> None:
        log_path = tmp_path / "transformations.log"
        logger.save(log_path)
        content = log_path.read_text(encoding="utf-8")
        assert content == ""
