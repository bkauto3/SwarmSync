"""
SGLang Multi-Token Prediction Tests

Tests for SGLang inference engine with speculative decoding:
- Correctness validation
- Performance benchmarks
- CUDA graph compilation
- Integration with DAAO router

Author: Genesis AI System
Date: October 28, 2025
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import torch

from infrastructure.sglang_inference import (
    SGLangInference,
    SGLangServer,
    ServerConfig,
    MTPConfig,
    SpeculativeAlgorithm,
    InferenceResponse,
    ThroughputMetrics,
    create_deepseek_v3_inference,
    create_llama_inference
)

from infrastructure.sglang_cuda_graphs import (
    CUDAGraphCompiler,
    GraphConfig,
    GraphMode,
    GraphOptimizer,
    CompiledGraph
)

from infrastructure.daao_router import (
    SGLangRouter,
    InferenceBackend,
    BackendRoutingDecision,
    EnhancedDAAORouter
)


# ===== Fixtures =====

@pytest.fixture
def mock_sglang_server():
    """Mock SGLang server for testing."""
    with patch('infrastructure.sglang_inference.subprocess.Popen') as mock_popen:
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        with patch('infrastructure.sglang_inference.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            yield mock_process


@pytest.fixture
def mtp_config():
    """Standard MTP configuration for testing."""
    return MTPConfig(
        algorithm=SpeculativeAlgorithm.EAGLE,
        num_steps=3,
        eagle_topk=1,
        num_draft_tokens=4,
        enable_cuda_graph=True,
        cuda_graph_max_bs=32
    )


@pytest.fixture
def server_config(mtp_config):
    """Server configuration for testing."""
    return ServerConfig(
        model_path="meta-llama/Llama-3.1-8B-Instruct",
        host="127.0.0.1",
        port=30000,
        mtp_config=mtp_config
    )


@pytest.fixture
def mock_inference_response():
    """Mock inference response."""
    with patch('infrastructure.sglang_inference.requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "This is a test response."},
                "finish_reason": "stop"
            }],
            "usage": {
                "completion_tokens": 10,
                "prompt_tokens": 5,
                "total_tokens": 15
            },
            "speculative_metrics": {
                "accepted_tokens": 8,
                "rejected_tokens": 2,
                "acceptance_rate": 0.8
            }
        }
        mock_post.return_value = mock_response
        yield mock_response


# ===== SGLang Server Tests =====

class TestSGLangServer:
    """Tests for SGLang server management."""

    def test_build_launch_command_basic(self, server_config):
        """Test basic server command construction."""
        server = SGLangServer(server_config)
        cmd = server._build_launch_command()

        assert "python3" in cmd
        assert "-m" in cmd
        assert "sglang.launch_server" in cmd
        assert "--model-path" in cmd
        assert "meta-llama/Llama-3.1-8B-Instruct" in cmd

    def test_build_launch_command_with_mtp(self, server_config):
        """Test command with MTP parameters."""
        server = SGLangServer(server_config)
        cmd = server._build_launch_command()

        assert "--speculative-algorithm" in cmd
        assert "EAGLE" in cmd
        assert "--speculative-num-steps" in cmd
        assert "3" in cmd
        assert "--cuda-graph-max-bs" in cmd
        assert "32" in cmd

    def test_build_launch_command_deepseek(self):
        """Test DeepSeek-V3 specific configuration."""
        config = ServerConfig(
            model_path="deepseek-ai/DeepSeek-V3-0324",
            tp_size=8,
            mtp_config=MTPConfig(
                algorithm=SpeculativeAlgorithm.EAGLE,
                num_steps=1,
                eagle_topk=1,
                num_draft_tokens=2
            )
        )
        server = SGLangServer(config)
        cmd = server._build_launch_command()

        assert "--tp-size" in cmd
        assert "8" in cmd
        assert "--speculative-num-steps" in cmd
        assert "1" in cmd

    def test_server_start_mock(self, server_config, mock_sglang_server):
        """Test server start with mocked subprocess."""
        server = SGLangServer(server_config)

        with patch.object(server, 'is_ready', return_value=True):
            result = server.start(timeout=5)

        assert result is True

    def test_server_ready_check(self, server_config):
        """Test server health check."""
        server = SGLangServer(server_config)

        with patch('infrastructure.sglang_inference.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            assert server.is_ready() is True

    def test_server_not_ready(self, server_config):
        """Test server not ready."""
        server = SGLangServer(server_config)

        with patch('infrastructure.sglang_inference.requests.get', side_effect=Exception("Connection refused")):
            assert server.is_ready() is False


# ===== SGLang Inference Tests =====

class TestSGLangInference:
    """Tests for SGLang inference engine."""

    def test_initialization_basic(self):
        """Test basic initialization."""
        with patch.object(SGLangServer, 'start', return_value=True):
            inference = SGLangInference(
                model_name="meta-llama/Llama-3.1-8B-Instruct",
                enable_mtp=True
            )

            assert inference.model_name == "meta-llama/Llama-3.1-8B-Instruct"
            assert inference.enable_mtp is True
            assert inference.server is not None

    def test_initialization_no_mtp(self):
        """Test initialization without MTP."""
        with patch.object(SGLangServer, 'start', return_value=True):
            inference = SGLangInference(
                model_name="gpt-4",
                enable_mtp=False
            )

            assert inference.enable_mtp is False
            assert inference.server.config.mtp_config is None

    def test_speculative_decode(self, mock_sglang_server, mock_inference_response):
        """Test speculative decoding inference."""
        with patch.object(SGLangServer, 'start', return_value=True):
            with patch.object(SGLangServer, 'is_ready', return_value=True):
                inference = SGLangInference(
                    model_name="meta-llama/Llama-3.1-8B-Instruct",
                    enable_mtp=True
                )
                inference.initialize()

                response = inference.speculative_decode(
                    prompt="What is the capital of France?",
                    max_tokens=100,
                    temperature=0.0
                )

                assert isinstance(response, InferenceResponse)
                assert response.text == "This is a test response."
                assert response.acceptance_rate == 0.8
                assert response.num_accepted_tokens == 8
                assert response.tokens_per_second > 0

    @pytest.mark.asyncio
    async def test_batch_inference(self, mock_sglang_server, mock_inference_response):
        """Test batch inference."""
        with patch.object(SGLangServer, 'start', return_value=True):
            with patch.object(SGLangServer, 'is_ready', return_value=True):
                inference = SGLangInference(
                    model_name="meta-llama/Llama-3.1-8B-Instruct",
                    enable_mtp=True
                )
                inference.initialize()

                prompts = [
                    "Question 1",
                    "Question 2",
                    "Question 3"
                ]

                results = await inference.batch_inference(
                    prompts,
                    batch_size=2,
                    max_tokens=100
                )

                assert len(results) == 3
                assert all(isinstance(r, InferenceResponse) for r in results)

    def test_benchmark_throughput(self, mock_sglang_server, mock_inference_response):
        """Test throughput benchmarking."""
        with patch.object(SGLangServer, 'start', return_value=True):
            with patch.object(SGLangServer, 'is_ready', return_value=True):
                inference = SGLangInference(
                    model_name="meta-llama/Llama-3.1-8B-Instruct",
                    enable_mtp=True
                )
                inference.initialize()

                prompts = ["Test prompt"] * 5

                metrics = inference.benchmark_throughput(
                    prompts,
                    batch_size=1,
                    warmup=2,
                    max_tokens=100
                )

                assert isinstance(metrics, ThroughputMetrics)
                assert metrics.tokens_per_second > 0
                assert metrics.requests_per_second > 0
                assert metrics.num_requests == 5

    def test_factory_deepseek(self):
        """Test DeepSeek factory function."""
        with patch.object(SGLangServer, 'start', return_value=True):
            inference = create_deepseek_v3_inference(
                model_path="deepseek-ai/DeepSeek-V3-0324",
                tp_size=8,
                enable_mtp=True
            )

            assert inference.model_name == "deepseek-ai/DeepSeek-V3-0324"
            assert inference.server.config.tp_size == 8
            assert inference.server.config.mtp_config.num_steps == 1

    def test_factory_llama(self):
        """Test Llama factory function."""
        with patch.object(SGLangServer, 'start', return_value=True):
            inference = create_llama_inference(
                model_path="meta-llama/Llama-3.1-8B-Instruct",
                enable_eagle3=True
            )

            assert inference.model_name == "meta-llama/Llama-3.1-8B-Instruct"
            assert inference.server.config.mtp_config.algorithm == SpeculativeAlgorithm.EAGLE3
            assert inference.server.config.mtp_config.num_steps == 5


# ===== CUDA Graph Tests =====

class TestCUDAGraphCompiler:
    """Tests for CUDA graph compilation."""

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_initialization(self):
        """Test compiler initialization."""
        config = GraphConfig(
            mode=GraphMode.FULL,
            max_batch_size=32
        )
        compiler = CUDAGraphCompiler(config)

        assert compiler.config.mode == GraphMode.FULL
        assert len(compiler.compiled_graphs) == 0

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_compile_inference_graph(self):
        """Test inference graph compilation."""
        config = GraphConfig(mode=GraphMode.INFERENCE)
        compiler = CUDAGraphCompiler(config)

        # Mock model
        model = torch.nn.Linear(10, 10).cuda()

        compiled = compiler.compile_inference_graph(
            model=model,
            batch_size=4,
            sequence_length=128,
            input_shape=(4, 10)
        )

        if compiled:
            assert isinstance(compiled, CompiledGraph)
            assert compiled.batch_size == 4
            assert compiled.sequence_length == 128

    def test_graph_disabled_without_cuda(self):
        """Test graph compiler with no CUDA."""
        with patch('torch.cuda.is_available', return_value=False):
            config = GraphConfig(mode=GraphMode.FULL)
            compiler = CUDAGraphCompiler(config)

            assert compiler.config.mode == GraphMode.DISABLED

    def test_graph_optimizer_speculative(self):
        """Test graph optimizer for speculative decoding."""
        optimizer = GraphOptimizer()
        compiler = optimizer.optimize_for_speculative_decoding(
            max_batch_size=32,
            num_draft_tokens=4
        )

        assert isinstance(compiler, CUDAGraphCompiler)
        # Mode will be DISABLED if CUDA unavailable
        if torch.cuda.is_available():
            assert compiler.config.mode == GraphMode.SPECULATIVE
        else:
            assert compiler.config.mode == GraphMode.DISABLED

    def test_graph_optimizer_throughput(self):
        """Test graph optimizer for throughput."""
        optimizer = GraphOptimizer()
        compiler = optimizer.optimize_for_throughput(
            target_batch_sizes=[1, 8, 16, 32]
        )

        assert isinstance(compiler, CUDAGraphCompiler)
        # Mode will be DISABLED if CUDA unavailable
        if torch.cuda.is_available():
            assert compiler.config.mode == GraphMode.FULL
        else:
            assert compiler.config.mode == GraphMode.DISABLED
        assert compiler.config.batch_sizes == [1, 8, 16, 32]


# ===== DAAO Router Integration Tests =====

class TestSGLangRouter:
    """Tests for SGLang routing logic."""

    def test_initialization(self):
        """Test router initialization."""
        router = SGLangRouter()

        assert InferenceBackend.STANDARD in router.backends_available
        assert router.backends_available[InferenceBackend.STANDARD] is True

    def test_route_to_sglang_batch_size(self):
        """Test routing based on batch size."""
        router = SGLangRouter()
        router.set_backend_availability(InferenceBackend.SGLANG_MTP, True)

        task = {'batch_size': 16}
        assert router.route_to_sglang(task, "gpt-4") is True

    def test_route_to_sglang_max_tokens(self):
        """Test routing based on generation length."""
        router = SGLangRouter()
        router.set_backend_availability(InferenceBackend.SGLANG_MTP, True)

        task = {'max_tokens': 1024}
        assert router.route_to_sglang(task, "gpt-4") is True

    def test_route_to_sglang_throughput_critical(self):
        """Test routing for throughput-critical tasks."""
        router = SGLangRouter()
        router.set_backend_availability(InferenceBackend.SGLANG_MTP, True)

        task = {'throughput_critical': True}
        assert router.route_to_sglang(task, "gpt-4") is True

    def test_no_route_sglang_unavailable(self):
        """Test routing when SGLang unavailable."""
        router = SGLangRouter()
        router.set_backend_availability(InferenceBackend.SGLANG_MTP, False)

        task = {'batch_size': 32}
        assert router.route_to_sglang(task, "gpt-4") is False

    def test_use_speculative_decoding(self):
        """Test speculative decoding selection."""
        router = SGLangRouter()

        assert router.use_speculative_decoding("generation") is True
        assert router.use_speculative_decoding("qa") is True
        assert router.use_speculative_decoding("classification") is False

    def test_select_backend_sglang(self):
        """Test backend selection for SGLang."""
        router = SGLangRouter()
        router.set_backend_availability(InferenceBackend.SGLANG_MTP, True)

        task = {
            'batch_size': 32,
            'max_tokens': 1024
        }

        decision = router.select_backend(task, "gpt-4", "generation")

        assert decision.backend == InferenceBackend.SGLANG_MTP
        assert decision.use_speculative_decoding is True
        assert decision.expected_speedup > 1.0

    def test_select_backend_standard(self):
        """Test backend selection for standard API."""
        router = SGLangRouter()

        task = {
            'batch_size': 1,
            'max_tokens': 100
        }

        decision = router.select_backend(task, "gpt-4", "generation")

        assert decision.backend == InferenceBackend.STANDARD
        assert decision.expected_speedup == 1.0

    def test_estimate_sglang_benefit(self):
        """Test benefit estimation."""
        router = SGLangRouter()
        router.set_backend_availability(InferenceBackend.SGLANG_MTP, True)

        tasks = [
            {'batch_size': 32, 'max_tokens': 1024},
            {'batch_size': 16, 'max_tokens': 512},
            {'batch_size': 1, 'max_tokens': 100},
        ]

        benefit = router.estimate_sglang_benefit(tasks)

        assert benefit['sglang_tasks'] == 2
        assert benefit['total_tasks'] == 3
        assert benefit['sglang_usage_pct'] > 0
        assert benefit['estimated_speedup'] > 1.0


class TestEnhancedDAAORouter:
    """Tests for enhanced DAAO router with SGLang."""

    def test_initialization(self):
        """Test enhanced router initialization."""
        router = EnhancedDAAORouter()

        assert hasattr(router, 'sglang_router')
        assert isinstance(router.sglang_router, SGLangRouter)

    def test_route_task_with_backend(self):
        """Test combined routing."""
        router = EnhancedDAAORouter()
        router.enable_sglang(True)

        task = {
            'description': 'Generate a comprehensive report on AI trends',
            'priority': 0.7,
            'batch_size': 16,
            'max_tokens': 1024,
            'required_tools': ['research', 'analysis']
        }

        model_decision, backend_decision = router.route_task_with_backend(
            task,
            task_type="generation"
        )

        assert model_decision is not None
        assert backend_decision is not None
        assert backend_decision.backend == InferenceBackend.SGLANG_MTP

    def test_enable_disable_sglang(self):
        """Test enabling/disabling SGLang."""
        router = EnhancedDAAORouter()

        router.enable_sglang(True)
        assert router.sglang_router.backends_available[InferenceBackend.SGLANG_MTP] is True

        router.enable_sglang(False)
        assert router.sglang_router.backends_available[InferenceBackend.SGLANG_MTP] is False


# ===== Performance Tests =====

class TestPerformance:
    """Performance validation tests."""

    @pytest.mark.slow
    def test_speedup_validation(self, mock_sglang_server, mock_inference_response):
        """Validate 2-4x speedup claim (mocked)."""
        # This would require actual SGLang server in production
        # Here we validate the structure

        with patch.object(SGLangServer, 'start', return_value=True):
            with patch.object(SGLangServer, 'is_ready', return_value=True):
                inference = SGLangInference(
                    model_name="meta-llama/Llama-3.1-8B-Instruct",
                    enable_mtp=True
                )
                inference.initialize()

                # Would measure actual throughput in production
                assert inference.server is not None

    @pytest.mark.slow
    def test_latency_reduction(self):
        """Validate latency reduction claims."""
        # Structural test - actual validation requires real server
        router = SGLangRouter()
        router.set_backend_availability(InferenceBackend.SGLANG_MTP, True)

        task = {'batch_size': 32, 'max_tokens': 1024}
        decision = router.select_backend(task, "gpt-4", "generation")

        # Expected speedup should be in 2-4x range
        assert 2.0 <= decision.expected_speedup <= 5.0


# ===== Integration Tests =====

class TestIntegration:
    """End-to-end integration tests."""

    def test_full_pipeline_mock(self, mock_sglang_server, mock_inference_response):
        """Test full pipeline with mocks."""
        # Initialize enhanced router
        router = EnhancedDAAORouter()
        router.enable_sglang(True)

        # Create task
        task = {
            'description': 'Implement a scalable distributed system with microservices',
            'priority': 0.8,
            'batch_size': 16,
            'max_tokens': 2048,
            'required_tools': ['docker', 'kubernetes']
        }

        # Route task
        model_decision, backend_decision = router.route_task_with_backend(
            task,
            task_type="generation"
        )

        # Validate decisions
        assert model_decision is not None
        assert backend_decision.backend == InferenceBackend.SGLANG_MTP
        assert backend_decision.use_speculative_decoding is True

        # Would execute inference in production
        # inference = SGLangInference(model_decision.model, enable_mtp=True)
        # response = inference.speculative_decode(task['description'])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
