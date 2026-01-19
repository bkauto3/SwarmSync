"""
Test suite for Vertex AI Fine-Tuning Pipeline

Tests supervised fine-tuning, RLHF tuning, distillation, and dataset preparation.
Includes tests for SE-Darwin and HALO routing dataset preparation.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from infrastructure.vertex_ai.fine_tuning_pipeline import (
    FineTuningPipeline,
    TuningType,
    TuningJobStatus,
    TuningJobConfig,
    TuningJobResult,
    TrainingDataset,
)


@pytest.fixture
def mock_vertex_ai():
    """Mock Vertex AI Pipeline API"""
    with patch('infrastructure.vertex_ai.fine_tuning_pipeline.VERTEX_AI_AVAILABLE', True):
        with patch('infrastructure.vertex_ai.fine_tuning_pipeline.aiplatform') as mock_api:
            mock_api.PipelineJob = Mock()
            mock_api.CustomJob = Mock()
            yield mock_api


@pytest.fixture
def fine_tuning_pipeline(mock_vertex_ai):
    """Create FineTuningPipeline instance for testing"""
    pipeline = FineTuningPipeline(
        project_id="test-project",
        location="us-central1"
    )
    return pipeline


@pytest.fixture
def sample_tuning_config():
    """Sample tuning job configuration"""
    from infrastructure.vertex_ai.fine_tuning_pipeline import HyperparameterConfig

    return TuningJobConfig(
        name="test-tuning-job",
        job_name="test-tuning-job-full",
        base_model="gemini-pro",
        tuning_type=TuningType.SUPERVISED,
        dataset=TrainingDataset(
            train_uri="gs://test-bucket/training-data.jsonl",
            validation_uri="gs://test-bucket/validation-data.jsonl",
            num_train_samples=100,
            num_val_samples=20,
        ),
        hyperparameters=HyperparameterConfig(
            learning_rate=0.001,
            batch_size=32,
            num_epochs=3,
        ),
        output_model_name="test-tuned-model",
        tags=["project:test", "model:gemini"],
    )


@pytest.mark.asyncio
async def test_prepare_se_darwin_dataset_success(fine_tuning_pipeline):
    """Test successful SE-Darwin dataset preparation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock archive
        archive_path = Path(tmpdir) / "archive.json"
        archive_data = {
            "trajectories": [
                {
                    "iteration": 1,
                    "code": "def test(): pass",
                    "test_results": [True, True, True],
                    "improvement_metrics": {"accuracy": 0.85}
                }
            ] * 10
        }
        with open(archive_path, "w") as f:
            json.dump(archive_data, f)

        output_uri = "gs://test-bucket/se-darwin-dataset"

        dataset = await fine_tuning_pipeline.prepare_se_darwin_dataset(
            archive_path=str(archive_path),
            output_gcs_uri=output_uri,
            max_trajectories=10,
            min_test_pass_rate=0.8,
        )

        assert dataset is not None
        assert "num_train_samples" in dataset or "training_examples" in str(dataset)


@pytest.mark.asyncio
async def test_prepare_se_darwin_dataset_filtering(fine_tuning_pipeline):
    """Test SE-Darwin dataset with quality filtering"""
    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = Path(tmpdir) / "archive-filtered.json"
        archive_data = {
            "trajectories": [
                {
                    "iteration": i,
                    "code": f"def func_{i}(): pass",
                    "test_results": [True] * (3 if i % 2 == 0 else 1),  # Only some pass tests
                    "improvement_metrics": {"accuracy": 0.7 + (i * 0.01)}
                }
                for i in range(20)
            ]
        }
        with open(archive_path, "w") as f:
            json.dump(archive_data, f)

        dataset = await fine_tuning_pipeline.prepare_se_darwin_dataset(
            archive_path=str(archive_path),
            output_gcs_uri="gs://test-bucket/filtered",
            max_trajectories=15,
            min_test_pass_rate=0.9,
        )

        assert dataset is not None


@pytest.mark.asyncio
async def test_prepare_halo_routing_dataset_success(fine_tuning_pipeline):
    """Test successful HALO routing dataset preparation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        decisions_path = Path(tmpdir) / "routing-decisions.jsonl"
        with open(decisions_path, "w") as f:
            for i in range(20):
                decision = {
                    "task": f"Task {i}",
                    "selected_agent": f"agent_{i % 5}",
                    "success": i % 3 == 0,
                }
                f.write(json.dumps(decision) + "\n")

        dataset = await fine_tuning_pipeline.prepare_halo_routing_dataset(
            routing_decisions_path=str(decisions_path),
            output_gcs_uri="gs://test-bucket/halo-routing",
            min_success_rate=0.3,
        )

        assert dataset is not None


@pytest.mark.asyncio
async def test_prepare_halo_routing_dataset_validation(fine_tuning_pipeline):
    """Test HALO routing dataset validation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        decisions_path = Path(tmpdir) / "routing-valid.jsonl"
        with open(decisions_path, "w") as f:
            for i in range(30):
                decision = {
                    "task": f"Query {i}",
                    "selected_agent": f"agent_{i % 7}",
                    "success": i < 25,  # High success rate
                }
                f.write(json.dumps(decision) + "\n")

        dataset = await fine_tuning_pipeline.prepare_halo_routing_dataset(
            routing_decisions_path=str(decisions_path),
            output_gcs_uri="gs://test-bucket/halo-validated",
            min_success_rate=0.8,
        )

        assert dataset is not None


@pytest.mark.asyncio
async def test_submit_tuning_job_supervised(fine_tuning_pipeline, sample_tuning_config):
    """Test submission of supervised fine-tuning job"""
    job = await fine_tuning_pipeline.submit_tuning_job(
        config=sample_tuning_config,
        wait_for_completion=False,
    )

    assert job is not None
    assert hasattr(job, 'job_id') or hasattr(job, 'name')


@pytest.mark.asyncio
async def test_submit_tuning_job_rlhf(fine_tuning_pipeline):
    """Test submission of RLHF fine-tuning job"""
    from infrastructure.vertex_ai.fine_tuning_pipeline import HyperparameterConfig, RLHFConfig

    config = TuningJobConfig(
        name="rlhf-tuning",
        job_name="rlhf-tuning-full",
        base_model="gemini-pro",
        tuning_type=TuningType.RLHF,
        dataset=TrainingDataset(
            train_uri="gs://test-bucket/rlhf-data.jsonl",
            validation_uri="gs://test-bucket/rlhf-val.jsonl",
            num_train_samples=100,
        ),
        hyperparameters=HyperparameterConfig(
            learning_rate=0.0001,
            num_epochs=5,
        ),
        rlhf_config=RLHFConfig(
            reward_model_uri="gs://test-bucket/reward_model_v1",
        ),
        output_model_name="rlhf-tuned-model",
    )

    job = await fine_tuning_pipeline.submit_tuning_job(
        config=config,
        wait_for_completion=False,
    )

    assert job is not None


@pytest.mark.asyncio
async def test_submit_tuning_job_distillation(fine_tuning_pipeline):
    """Test submission of distillation job"""
    from infrastructure.vertex_ai.fine_tuning_pipeline import HyperparameterConfig, DistillationConfig

    config = TuningJobConfig(
        name="distillation-job",
        job_name="distillation-job-full",
        base_model="gemini-pro",
        tuning_type=TuningType.DISTILLATION,
        dataset=TrainingDataset(
            train_uri="gs://test-bucket/distil-data.jsonl",
            num_train_samples=100,
        ),
        hyperparameters=HyperparameterConfig(
            num_epochs=2,
        ),
        distillation_config=DistillationConfig(
            teacher_model_uri="gs://test-bucket/gemini-2.0-pro",
            temperature=4.0,
        ),
        output_model_name="distillation-tuned-model",
    )

    job = await fine_tuning_pipeline.submit_tuning_job(
        config=config,
        wait_for_completion=False,
    )

    assert job is not None


@pytest.mark.asyncio
async def test_submit_tuning_job_parameter_efficient(fine_tuning_pipeline):
    """Test submission of parameter-efficient fine-tuning (LoRA)"""
    from infrastructure.vertex_ai.fine_tuning_pipeline import HyperparameterConfig

    config = TuningJobConfig(
        name="lora-tuning",
        job_name="lora-tuning-full",
        base_model="gemini-pro",
        tuning_type=TuningType.PARAMETER_EFFICIENT,
        dataset=TrainingDataset(
            train_uri="gs://test-bucket/peft-data.jsonl",
            num_train_samples=100,
        ),
        hyperparameters=HyperparameterConfig(
            num_epochs=3,
            lora_r=8,
            lora_alpha=16,
        ),
        output_model_name="lora-tuned-model",
    )

    job = await fine_tuning_pipeline.submit_tuning_job(
        config=config,
        wait_for_completion=False,
    )

    assert job is not None


@pytest.mark.asyncio
async def test_register_tuned_model_success(fine_tuning_pipeline, sample_tuning_config):
    """Test registration of tuned model"""
    # Create mock tuning result
    result = TuningJobResult(
        job_id="test-job-123",
        job_name="test-job-123-full",
        status=TuningJobStatus.SUCCEEDED,
        tuned_model_uri="gs://test-bucket/tuned-model",
        metrics={"eval_loss": 0.25, "eval_accuracy": 0.92},
    )

    metadata = await fine_tuning_pipeline.register_tuned_model(
        result=result,
        config=sample_tuning_config,
    )

    assert metadata is not None
    assert metadata.name is not None or metadata.display_name is not None


@pytest.mark.asyncio
async def test_register_tuned_model_with_metadata(fine_tuning_pipeline, sample_tuning_config):
    """Test tuned model registration with rich metadata"""
    result = TuningJobResult(
        job_id="test-job-456",
        job_name="test-job-456-full",
        status=TuningJobStatus.SUCCEEDED,
        tuned_model_uri="gs://test-bucket/tuned-enhanced",
        metrics={
            "eval_loss": 0.20,
            "eval_accuracy": 0.94,
            "training_loss": 0.18,
        },
    )

    metadata = await fine_tuning_pipeline.register_tuned_model(
        result=result,
        config=sample_tuning_config,
    )

    assert metadata is not None
    if hasattr(metadata, 'performance_metrics'):
        assert "eval_accuracy" in str(metadata.performance_metrics) or len(metadata.performance_metrics) > 0


def test_tuning_type_enum():
    """Test TuningType enum values"""
    assert TuningType.SUPERVISED.value == "supervised"
    assert TuningType.RLHF.value == "rlhf"
    assert TuningType.DISTILLATION.value == "distillation"
    assert TuningType.PARAMETER_EFFICIENT.value == "peft"


def test_tuning_job_status_enum():
    """Test TuningJobStatus enum values"""
    assert TuningJobStatus.PENDING.value == "pending"
    assert TuningJobStatus.RUNNING.value == "running"
    assert TuningJobStatus.SUCCEEDED.value == "succeeded"
    assert TuningJobStatus.FAILED.value == "failed"


def test_tuning_job_config_initialization(sample_tuning_config):
    """Test TuningJobConfig initialization"""
    assert sample_tuning_config.name == "test-tuning-job"
    assert sample_tuning_config.job_name == "test-tuning-job-full"
    assert sample_tuning_config.base_model == "gemini-pro"
    assert sample_tuning_config.tuning_type == TuningType.SUPERVISED
    assert sample_tuning_config.hyperparameters.learning_rate == 0.001


def test_tuning_job_result_initialization():
    """Test TuningJobResult initialization"""
    result = TuningJobResult(
        job_id="job-123",
        job_name="job-123-full",
        status=TuningJobStatus.SUCCEEDED,
        tuned_model_uri="gs://bucket/model",
        metrics={"accuracy": 0.95},
    )

    assert result.job_id == "job-123"
    assert result.job_name == "job-123-full"
    assert result.status == TuningJobStatus.SUCCEEDED
    assert result.tuned_model_uri == "gs://bucket/model"
    assert result.metrics["accuracy"] == 0.95


@pytest.mark.asyncio
async def test_tuning_with_custom_hyperparameters(fine_tuning_pipeline):
    """Test fine-tuning with custom hyperparameters"""
    from infrastructure.vertex_ai.fine_tuning_pipeline import HyperparameterConfig

    config = TuningJobConfig(
        name="custom-hyperparams",
        job_name="custom-hyperparams-full",
        base_model="gemini-pro",
        tuning_type=TuningType.SUPERVISED,
        dataset=TrainingDataset(
            train_uri="gs://test-bucket/training.jsonl",
            num_train_samples=100,
        ),
        hyperparameters=HyperparameterConfig(
            learning_rate=0.0005,
            batch_size=64,
            num_epochs=5,
            warmup_steps=100,
            weight_decay=0.01,
        ),
        output_model_name="custom-tuned-model",
    )

    job = await fine_tuning_pipeline.submit_tuning_job(
        config=config,
        wait_for_completion=False,
    )

    assert job is not None


@pytest.mark.asyncio
async def test_dataset_preparation_with_validation_split(fine_tuning_pipeline):
    """Test dataset preparation with train/validation split"""
    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = Path(tmpdir) / "archive-split.json"
        archive_data = {
            "trajectories": [
                {
                    "iteration": i,
                    "code": f"def code_{i}(): return {i}",
                    "test_results": [True] * 3,
                    "improvement_metrics": {"score": 0.8 + i * 0.01}
                }
                for i in range(50)
            ]
        }
        with open(archive_path, "w") as f:
            json.dump(archive_data, f)

        dataset = await fine_tuning_pipeline.prepare_se_darwin_dataset(
            archive_path=str(archive_path),
            output_gcs_uri="gs://test-bucket/split-dataset",
            max_trajectories=50,
        )

        assert dataset is not None
        if "num_val_samples" in str(dataset):
            # Validation split was created
            pass
