"""
Comprehensive Test Suite for Issue 6 Fixes - Blocked Dependencies & Schema Issues

ISSUE 6 COVERAGE:
1. SE-Darwin Trajectory schema completeness (code_after, strategy_description, plan_id)
2. Hybrid RAG initialization with numpy fallback
3. OCR cache warmup functionality
4. Performance benchmark suite structure
5. Trajectory memory pruning logic

Author: Thon (Python Expert)
Date: October 25, 2025
Status: Validation suite for Issue 6 resolution
"""

import asyncio
import json
import logging
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Helper function to check pytesseract availability
def _check_pytesseract_available() -> bool:
    """Check if pytesseract is available for tests"""
    try:
        import pytesseract
        return True
    except ImportError:
        return False


# ============================================================================
# PART 1: SE-Darwin Trajectory Schema Tests
# ============================================================================

class TestTrajectorySchemaCompleteness:
    """Validate all required trajectory schema fields are present"""

    def test_trajectory_has_code_after_field(self):
        """ISSUE 6 FIX: Verify code_after field exists in Trajectory dataclass"""
        from infrastructure.trajectory_pool import Trajectory

        # Create trajectory with code_after
        traj = Trajectory(
            trajectory_id="test_001",
            generation=0,
            agent_name="builder",
            code_after="def updated_function():\n    pass"
        )

        assert hasattr(traj, 'code_after'), "Trajectory missing code_after field"
        assert traj.code_after == "def updated_function():\n    pass"
        logger.info("✓ code_after field present and functional")

    def test_trajectory_has_strategy_description_field(self):
        """ISSUE 6 FIX: Verify strategy_description field exists"""
        from infrastructure.trajectory_pool import Trajectory

        traj = Trajectory(
            trajectory_id="test_002",
            generation=0,
            agent_name="builder",
            strategy_description="Use iterative refinement approach"
        )

        assert hasattr(traj, 'strategy_description'), "Trajectory missing strategy_description"
        assert traj.strategy_description == "Use iterative refinement approach"
        logger.info("✓ strategy_description field present and functional")

    def test_trajectory_has_plan_id_field(self):
        """ISSUE 6 FIX: Verify plan_id field exists for production learning"""
        from infrastructure.trajectory_pool import Trajectory

        traj = Trajectory(
            trajectory_id="test_003",
            generation=0,
            agent_name="builder",
            plan_id="plan_abc123"
        )

        assert hasattr(traj, 'plan_id'), "Trajectory missing plan_id field"
        assert traj.plan_id == "plan_abc123"
        logger.info("✓ plan_id field present and functional")

    def test_trajectory_schema_serialization_includes_new_fields(self):
        """Verify new fields are included in to_compact_dict() serialization"""
        from infrastructure.trajectory_pool import Trajectory

        traj = Trajectory(
            trajectory_id="test_004",
            generation=0,
            agent_name="builder",
            code_after="# Final code",
            strategy_description="Multi-stage approach",
            plan_id="plan_xyz789"
        )

        compact_dict = traj.to_compact_dict()

        assert 'code_after' in compact_dict, "code_after not in serialized dict"
        assert 'strategy_description' in compact_dict, "strategy_description not in serialized dict"
        assert 'plan_id' in compact_dict, "plan_id not in serialized dict"
        logger.info("✓ All new fields serialize correctly")

    def test_trajectory_defaults_for_optional_fields(self):
        """Verify optional fields have sensible defaults"""
        from infrastructure.trajectory_pool import Trajectory

        # Create trajectory without specifying optional fields
        traj = Trajectory(
            trajectory_id="test_005",
            generation=0,
            agent_name="builder"
        )

        assert traj.code_after is None, "code_after should default to None"
        assert traj.strategy_description == "", "strategy_description should default to empty string"
        assert traj.plan_id is None, "plan_id should default to None"
        logger.info("✓ Optional field defaults correct")


# ============================================================================
# PART 2: Hybrid RAG Initialization Tests
# ============================================================================

class TestHybridRAGInitialization:
    """Validate Hybrid RAG graceful initialization with missing dependencies"""

    def test_hybrid_rag_checks_numpy_availability(self):
        """ISSUE 6 FIX: Verify numpy availability check at initialization"""
        from infrastructure.hybrid_rag_retriever import HAS_NUMPY

        # Check that HAS_NUMPY flag is set correctly
        import sys
        if 'numpy' in sys.modules:
            assert HAS_NUMPY is True, "HAS_NUMPY should be True when numpy is available"
        else:
            assert HAS_NUMPY is False, "HAS_NUMPY should be False when numpy is missing"

        logger.info(f"✓ Numpy availability check: HAS_NUMPY={HAS_NUMPY}")

    def test_hybrid_rag_raises_error_without_numpy(self):
        """Verify HybridRAGRetriever raises RuntimeError if numpy is missing"""
        # Mock numpy as unavailable
        with patch('infrastructure.hybrid_rag_retriever.HAS_NUMPY', False):
            with patch('infrastructure.hybrid_rag_retriever.np', None):
                from infrastructure.hybrid_rag_retriever import HybridRAGRetriever

                mock_vector_db = MagicMock()
                mock_graph_db = MagicMock()
                mock_embedding_gen = MagicMock()

                with pytest.raises(RuntimeError, match="Hybrid RAG requires numpy"):
                    HybridRAGRetriever(
                        vector_db=mock_vector_db,
                        graph_db=mock_graph_db,
                        embedding_generator=mock_embedding_gen
                    )

        logger.info("✓ RuntimeError raised when numpy unavailable")

    def test_hybrid_rag_validates_at_least_one_db(self):
        """ISSUE 6 FIX: Verify at least one retrieval system is required"""
        from infrastructure.hybrid_rag_retriever import HybridRAGRetriever

        mock_embedding_gen = MagicMock()

        # Both dbs are None - should raise ValueError
        with pytest.raises(ValueError, match="At least one of vector_db or graph_db"):
            HybridRAGRetriever(
                vector_db=None,
                graph_db=None,
                embedding_generator=mock_embedding_gen
            )

        logger.info("✓ ValueError raised when both DBs are None")

    def test_hybrid_rag_initializes_with_vector_only(self):
        """Verify HybridRAG can initialize with vector DB only"""
        from infrastructure.hybrid_rag_retriever import HybridRAGRetriever

        mock_vector_db = MagicMock()
        mock_embedding_gen = MagicMock()

        # Should succeed with vector_db only
        retriever = HybridRAGRetriever(
            vector_db=mock_vector_db,
            graph_db=None,
            embedding_generator=mock_embedding_gen
        )

        assert retriever.vector_db is not None
        assert retriever.graph_db is None
        logger.info("✓ Initialization succeeds with vector DB only")

    def test_hybrid_rag_initializes_with_graph_only(self):
        """Verify HybridRAG can initialize with graph DB only"""
        from infrastructure.hybrid_rag_retriever import HybridRAGRetriever

        mock_graph_db = MagicMock()
        mock_embedding_gen = MagicMock()

        # Should succeed with graph_db only
        retriever = HybridRAGRetriever(
            vector_db=None,
            graph_db=mock_graph_db,
            embedding_generator=mock_embedding_gen
        )

        assert retriever.vector_db is None
        assert retriever.graph_db is not None
        logger.info("✓ Initialization succeeds with graph DB only")


# ============================================================================
# PART 3: OCR Cache Warmup Tests
# ============================================================================

class TestOCRCacheWarmup:
    """Validate OCR cache warmup functionality"""

    def test_ocr_service_has_warmup_cache_method(self):
        """ISSUE 6 FIX: Verify warmup_cache method exists in DeepSeekOCRService"""
        from infrastructure.ocr.deepseek_ocr_service import DeepSeekOCRService

        service = DeepSeekOCRService()
        assert hasattr(service, 'warmup_cache'), "DeepSeekOCRService missing warmup_cache method"
        assert callable(service.warmup_cache), "warmup_cache should be callable"
        logger.info("✓ warmup_cache method exists and is callable")

    def test_warmup_cache_returns_expected_structure(self):
        """Verify warmup_cache returns correct statistics structure"""
        from infrastructure.ocr.deepseek_ocr_service import DeepSeekOCRService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = DeepSeekOCRService(cache_dir=tmpdir)

            # Run warmup with no sample images (should handle gracefully)
            result = service.warmup_cache(sample_images=[], modes=["raw"])

            assert isinstance(result, dict), "warmup_cache should return dict"
            assert 'images_processed' in result
            assert 'cache_entries_created' in result
            assert 'total_warmup_time' in result
            assert 'failures' in result
            assert 'success_rate' in result

            logger.info(f"✓ warmup_cache returns expected structure: {result.keys()}")

    def test_warmup_cache_handles_missing_images_gracefully(self):
        """Verify warmup_cache handles missing sample images without crashing"""
        from infrastructure.ocr.deepseek_ocr_service import DeepSeekOCRService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = DeepSeekOCRService(cache_dir=tmpdir)

            # Non-existent image paths
            fake_images = ["/nonexistent/image1.png", "/nonexistent/image2.png"]
            result = service.warmup_cache(sample_images=fake_images, modes=["raw"])

            assert result['images_processed'] == 0, "Should not process non-existent images"
            assert len(result['failures']) == 2, "Should record 2 failures"
            assert result['cache_entries_created'] == 0, "Should create 0 cache entries"

            logger.info("✓ warmup_cache handles missing images gracefully")

    @pytest.mark.skipif(
        not _check_pytesseract_available(),
        reason="pytesseract not installed"
    )
    def test_warmup_cache_creates_cache_entries(self):
        """Verify warmup_cache actually creates cache files when given valid images"""
        from infrastructure.ocr.deepseek_ocr_service import DeepSeekOCRService
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test image
            test_image_path = Path(tmpdir) / "test_image.png"
            img = Image.new('RGB', (100, 100), color='white')
            img.save(test_image_path)

            # Create service with separate cache dir
            cache_dir = Path(tmpdir) / "cache"
            service = DeepSeekOCRService(cache_dir=str(cache_dir))

            # Warmup cache with test image
            result = service.warmup_cache(
                sample_images=[str(test_image_path)],
                modes=["raw"]
            )

            # Verify cache entries were created
            assert result['cache_entries_created'] >= 1, "Should create at least 1 cache entry"
            assert result['success_rate'] > 0, "Success rate should be > 0%"

            # Verify cache files exist
            cache_files = list(cache_dir.glob("*.json"))
            assert len(cache_files) >= 1, "Cache directory should contain JSON files"

            logger.info(f"✓ warmup_cache creates cache entries: {result['cache_entries_created']} created")

    @pytest.mark.skipif(
        not _check_pytesseract_available(),
        reason="pytesseract not installed"
    )
    def test_warmup_cache_supports_multiple_modes(self):
        """Verify warmup_cache processes multiple OCR modes"""
        from infrastructure.ocr.deepseek_ocr_service import DeepSeekOCRService
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test image
            test_image_path = Path(tmpdir) / "test.png"
            img = Image.new('RGB', (100, 100), color='white')
            img.save(test_image_path)

            cache_dir = Path(tmpdir) / "cache"
            service = DeepSeekOCRService(cache_dir=str(cache_dir))

            # Warmup with 2 modes
            result = service.warmup_cache(
                sample_images=[str(test_image_path)],
                modes=["document", "raw"]
            )

            # Should create 2 cache entries (1 image × 2 modes)
            assert result['cache_entries_created'] == 2, f"Expected 2 cache entries, got {result['cache_entries_created']}"

            logger.info("✓ warmup_cache supports multiple modes")


# ============================================================================
# PART 4: Performance Benchmark Suite Tests
# ============================================================================

class TestPerformanceBenchmarkSuite:
    """Validate performance benchmark suite structure"""

    def test_performance_benchmarks_file_exists(self):
        """Verify performance benchmark test file exists"""
        benchmark_file = Path("/home/genesis/genesis-rebuild/tests/test_performance_benchmarks.py")
        assert benchmark_file.exists(), "test_performance_benchmarks.py should exist"
        logger.info("✓ Performance benchmark file exists")

    def test_benchmark_tasks_class_exists(self):
        """Verify BenchmarkTasks class with task categories"""
        from tests.test_performance_benchmarks import BenchmarkTasks

        assert hasattr(BenchmarkTasks, 'SIMPLE_TASKS'), "BenchmarkTasks missing SIMPLE_TASKS"
        assert hasattr(BenchmarkTasks, 'MEDIUM_TASKS'), "BenchmarkTasks missing MEDIUM_TASKS"

        # Verify structure
        assert isinstance(BenchmarkTasks.SIMPLE_TASKS, list), "SIMPLE_TASKS should be a list"
        assert len(BenchmarkTasks.SIMPLE_TASKS) > 0, "SIMPLE_TASKS should not be empty"

        logger.info(f"✓ BenchmarkTasks class exists with {len(BenchmarkTasks.SIMPLE_TASKS)} simple tasks")

    def test_benchmark_result_dataclass_exists(self):
        """Verify BenchmarkResult dataclass structure"""
        from tests.test_performance_benchmarks import BenchmarkResult

        # Create a result
        result = BenchmarkResult(
            task_id="test_001",
            task_description="Test task",
            execution_time=1.5,
            success=True
        )

        assert result.task_id == "test_001"
        assert result.execution_time == 1.5
        assert result.success is True

        logger.info("✓ BenchmarkResult dataclass structure correct")

    def test_benchmark_suite_dataclass_exists(self):
        """Verify BenchmarkSuite dataclass with aggregation methods"""
        from tests.test_performance_benchmarks import BenchmarkSuite, BenchmarkResult
        from datetime import datetime

        suite = BenchmarkSuite(
            version="v2.0",
            run_timestamp=datetime.now(),
            results=[]
        )

        assert hasattr(suite, 'get_success_rate'), "BenchmarkSuite missing get_success_rate"
        assert hasattr(suite, 'get_avg_execution_time'), "BenchmarkSuite missing get_avg_execution_time"
        assert hasattr(suite, 'get_total_cost'), "BenchmarkSuite missing get_total_cost"

        logger.info("✓ BenchmarkSuite dataclass with aggregation methods exists")


# ============================================================================
# PART 5: Trajectory Memory Pruning Tests
# ============================================================================

class TestTrajectoryMemoryPruning:
    """Validate trajectory pool pruning logic"""

    def test_trajectory_pool_has_prune_method(self):
        """Verify TrajectoryPool has _prune_low_performers method"""
        from infrastructure.trajectory_pool import TrajectoryPool

        with tempfile.TemporaryDirectory() as tmpdir:
            pool = TrajectoryPool(
                agent_name="test_agent",
                max_trajectories=10,
                storage_dir=Path(tmpdir)
            )

            assert hasattr(pool, '_prune_low_performers'), "TrajectoryPool missing _prune_low_performers"
            assert callable(pool._prune_low_performers), "_prune_low_performers should be callable"

            logger.info("✓ TrajectoryPool has _prune_low_performers method")

    def test_trajectory_pruning_triggered_on_capacity_exceed(self):
        """Verify pruning is triggered when pool exceeds max_trajectories"""
        from infrastructure.trajectory_pool import TrajectoryPool, Trajectory

        with tempfile.TemporaryDirectory() as tmpdir:
            pool = TrajectoryPool(
                agent_name="test_agent",
                max_trajectories=3,
                storage_dir=Path(tmpdir)
            )

            # Add 5 trajectories (exceeds max of 3)
            for i in range(5):
                traj = Trajectory(
                    trajectory_id=f"test_{i}",
                    generation=0,
                    agent_name="test_agent",
                    success_score=0.1 * i  # Increasing scores
                )
                pool.add_trajectory(traj)

            # Should have pruned lowest performers
            assert len(pool.trajectories) <= 3, f"Pool should prune to max_trajectories, has {len(pool.trajectories)}"
            assert pool.total_pruned >= 2, f"Should have pruned at least 2 trajectories, pruned {pool.total_pruned}"

            logger.info(f"✓ Pruning triggered: {pool.total_pruned} trajectories pruned")

    def test_pruning_keeps_successful_trajectories(self):
        """Verify pruning preserves successful trajectories"""
        from infrastructure.trajectory_pool import TrajectoryPool, Trajectory

        with tempfile.TemporaryDirectory() as tmpdir:
            pool = TrajectoryPool(
                agent_name="test_agent",
                max_trajectories=3,
                success_threshold=0.7,
                storage_dir=Path(tmpdir)
            )

            # Add successful trajectory
            successful_traj = Trajectory(
                trajectory_id="successful_1",
                generation=0,
                agent_name="test_agent",
                success_score=0.8
            )
            pool.add_trajectory(successful_traj)

            # Add many low-scoring trajectories
            for i in range(5):
                traj = Trajectory(
                    trajectory_id=f"low_{i}",
                    generation=0,
                    agent_name="test_agent",
                    success_score=0.2
                )
                pool.add_trajectory(traj)

            # Successful trajectory should still be in pool
            assert "successful_1" in pool.trajectories, "Successful trajectory should not be pruned"

            logger.info("✓ Pruning preserves successful trajectories")

    def test_pruning_keeps_recent_trajectories(self):
        """Verify pruning preserves trajectories from recent generations"""
        from infrastructure.trajectory_pool import TrajectoryPool, Trajectory

        with tempfile.TemporaryDirectory() as tmpdir:
            pool = TrajectoryPool(
                agent_name="test_agent",
                max_trajectories=3,
                storage_dir=Path(tmpdir)
            )

            # Add old low-scoring trajectory
            old_traj = Trajectory(
                trajectory_id="old_1",
                generation=0,
                agent_name="test_agent",
                success_score=0.3
            )
            pool.add_trajectory(old_traj)

            # Add recent low-scoring trajectories
            for i in range(3):
                traj = Trajectory(
                    trajectory_id=f"recent_{i}",
                    generation=20,  # Recent generation
                    agent_name="test_agent",
                    success_score=0.3
                )
                pool.add_trajectory(traj)

            # Old trajectory should be pruned, recent should remain
            assert "old_1" not in pool.trajectories, "Old trajectory should be pruned"

            logger.info("✓ Pruning preserves recent trajectories")

    def test_pruning_statistics_tracked(self):
        """Verify pruning statistics are tracked in pool"""
        from infrastructure.trajectory_pool import TrajectoryPool, Trajectory

        with tempfile.TemporaryDirectory() as tmpdir:
            pool = TrajectoryPool(
                agent_name="test_agent",
                max_trajectories=2,
                storage_dir=Path(tmpdir)
            )

            initial_pruned = pool.total_pruned

            # Add trajectories to trigger pruning
            for i in range(5):
                traj = Trajectory(
                    trajectory_id=f"test_{i}",
                    generation=0,
                    agent_name="test_agent",
                    success_score=0.1
                )
                pool.add_trajectory(traj)

            # Check statistics
            stats = pool.get_statistics()
            assert 'total_added' in stats
            assert 'total_pruned' in stats
            assert stats['total_pruned'] > initial_pruned, "total_pruned should increase"

            logger.info(f"✓ Pruning statistics tracked: {stats['total_pruned']} total pruned")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIssue6Integration:
    """Integration tests verifying all Issue 6 fixes work together"""

    def test_trajectory_pool_persistence_includes_new_fields(self):
        """Verify trajectory persistence includes code_after, strategy_description, plan_id"""
        from infrastructure.trajectory_pool import TrajectoryPool, Trajectory

        with tempfile.TemporaryDirectory() as tmpdir:
            pool = TrajectoryPool(
                agent_name="test_agent",
                storage_dir=Path(tmpdir)
            )

            # Add trajectory with new fields
            traj = Trajectory(
                trajectory_id="persist_test",
                generation=0,
                agent_name="test_agent",
                code_after="# Final code",
                strategy_description="Test strategy",
                plan_id="plan_123"
            )
            pool.add_trajectory(traj)

            # Save to disk
            save_path = pool.save_to_disk()
            assert save_path.exists(), "Save file should exist"

            # Load from disk
            loaded_pool = TrajectoryPool.load_from_disk(
                agent_name="test_agent",
                storage_dir=Path(tmpdir)
            )

            # Verify new fields persisted
            loaded_traj = loaded_pool.get_trajectory("persist_test")
            assert loaded_traj is not None
            assert loaded_traj.code_after == "# Final code"
            assert loaded_traj.strategy_description == "Test strategy"
            assert loaded_traj.plan_id == "plan_123"

            logger.info("✓ Trajectory persistence includes all new fields")

    def test_all_issue_6_fixes_documented(self):
        """Verify all Issue 6 fixes are properly documented in code"""
        import re

        files_to_check = [
            "/home/genesis/genesis-rebuild/infrastructure/trajectory_pool.py",
            "/home/genesis/genesis-rebuild/infrastructure/hybrid_rag_retriever.py",
            "/home/genesis/genesis-rebuild/infrastructure/ocr/deepseek_ocr_service.py"
        ]

        for file_path in files_to_check:
            with open(file_path, 'r') as f:
                content = f.read()
                # Check for ISSUE 6 documentation
                assert 'ISSUE 6' in content or 'Issue 6' in content, \
                    f"{file_path} should document Issue 6 fixes"

        logger.info("✓ All Issue 6 fixes are documented in code")


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

@pytest.fixture(autouse=True)
def setup_logging():
    """Configure logging for all tests"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
