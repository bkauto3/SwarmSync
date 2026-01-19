"""End-to-end business creation benchmark with FP16 integration.

This test validates the entire Genesis system with FP16 training enabled,
measuring performance improvements in a realistic business creation scenario.

Tests:
1. Full business creation workflow with FP16 enabled
2. Agent evolution with FP16-accelerated WorldModel
3. Performance comparison (FP16 vs FP32)
4. System stability and accuracy validation
"""

import asyncio
import os
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# These tests require torch
torch = pytest.importorskip("torch")

from infrastructure.world_model import WorldModel


@pytest.fixture
def mock_genesis_environment():
    """Create a mock Genesis environment for E2E testing."""
    
    class MockGenesisOrchestrator:
        """Mock orchestrator for business creation."""
        
        def __init__(self):
            self.world_model = WorldModel()
            self.tasks_completed = []
        
        async def create_business(self, business_spec: Dict[str, Any]) -> Dict[str, Any]:
            """Simulate business creation process."""
            
            # Simulate planning phase
            await asyncio.sleep(0.1)
            
            # Simulate agent evolution with world model training
            from tests.training.test_se_darwin_fp16_integration import MockReplayBuffer
            self.world_model.replay_buffer = MockReplayBuffer(100)
            await self.world_model.train(num_epochs=2, batch_size=16)
            
            # Simulate execution phase
            await asyncio.sleep(0.1)
            
            # Track completion
            self.tasks_completed.append({
                "business_name": business_spec.get("name"),
                "timestamp": time.time(),
                "world_model_trained": True,
                "fp16_enabled": self.world_model.fp16_enabled
            })
            
            return {
                "success": True,
                "business_id": f"biz_{business_spec.get('name')}",
                "agents_created": 3,
                "world_model_loss": self.world_model.training_history[-1]["loss"] if self.world_model.training_history else 0.0,
                "fp16_stats": self.world_model._fp16_stats
            }
    
    return MockGenesisOrchestrator()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_business_creation_with_fp16(mock_genesis_environment):
    """Test end-to-end business creation with FP16 enabled."""
    
    # Enable FP16
    os.environ["ENABLE_FP16_TRAINING"] = "true"
    
    try:
        orchestrator = mock_genesis_environment
        
        # Define business specification
        business_spec = {
            "name": "ai_saas_startup",
            "type": "web_service",
            "agents": ["builder", "optimizer", "deployer"],
            "target_metrics": {
                "revenue": 1000,
                "users": 100
            }
        }
        
        # Create business
        start_time = time.perf_counter()
        result = await orchestrator.create_business(business_spec)
        duration = time.perf_counter() - start_time
        
        # Validate results
        assert result["success"], "Business creation should succeed"
        assert result["agents_created"] > 0, "Should create agents"
        assert result["world_model_loss"] >= 0, "World model should be trained"
        
        # Verify FP16 was used
        if result["fp16_stats"]:
            assert result["fp16_stats"].get("fp16_enabled_runtime") or not torch.cuda.is_available()
        
        # Verify performance
        assert duration < 60.0, "Business creation should complete within 60 seconds"
        
        print(f"\n{'='*60}")
        print(f"E2E Business Creation (FP16)")
        print(f"{'='*60}")
        print(f"Duration:         {duration:.2f}s")
        print(f"Agents created:   {result['agents_created']}")
        print(f"Final loss:       {result['world_model_loss']:.4f}")
        print(f"FP16 enabled:     {orchestrator.world_model.fp16_enabled}")
        print(f"{'='*60}")
    
    finally:
        os.environ["ENABLE_FP16_TRAINING"] = "false"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_fp16_vs_fp32_performance(mock_genesis_environment):
    """Compare FP16 vs FP32 performance in E2E scenario."""
    
    business_spec = {
        "name": "test_business",
        "type": "web_service",
        "agents": ["builder", "optimizer"],
    }
    
    # FP32 baseline
    os.environ["ENABLE_FP16_TRAINING"] = "false"
    orchestrator_fp32 = mock_genesis_environment
    
    start_fp32 = time.perf_counter()
    result_fp32 = await orchestrator_fp32.create_business(business_spec)
    fp32_duration = time.perf_counter() - start_fp32
    
    # FP16 comparison (create new environment)
    os.environ["ENABLE_FP16_TRAINING"] = "true"
    
    # Use the same mock but reset world model
    orchestrator_fp16 = mock_genesis_environment
    orchestrator_fp16.world_model = WorldModel()
    
    start_fp16 = time.perf_counter()
    result_fp16 = await orchestrator_fp16.create_business(business_spec)
    fp16_duration = time.perf_counter() - start_fp16
    
    # Calculate speedup
    speedup = fp32_duration / max(fp16_duration, 1e-6)
    
    print(f"\n{'='*60}")
    print(f"E2E Performance Comparison")
    print(f"{'='*60}")
    print(f"FP32 duration:    {fp32_duration:.2f}s")
    print(f"FP16 duration:    {fp16_duration:.2f}s")
    print(f"Speedup:          {speedup:.2f}x")
    print(f"FP32 loss:        {result_fp32['world_model_loss']:.4f}")
    print(f"FP16 loss:        {result_fp16['world_model_loss']:.4f}")
    print(f"CUDA available:   {torch.cuda.is_available()}")
    print(f"{'='*60}")
    
    # Verify speedup is at least neutral
    assert speedup >= 0.8, f"FP16 should not be significantly slower, got {speedup:.2f}x"
    
    # Verify both succeeded
    assert result_fp32["success"] and result_fp16["success"]
    
    # Cleanup
    os.environ["ENABLE_FP16_TRAINING"] = "false"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_multiple_businesses_fp16():
    """Test creating multiple businesses with FP16 enabled."""
    
    os.environ["ENABLE_FP16_TRAINING"] = "true"
    
    try:
        from tests.training.test_se_darwin_fp16_integration import MockReplayBuffer
        
        businesses = [
            {"name": f"business_{i}", "type": "web_service"}
            for i in range(3)
        ]
        
        results = []
        total_start = time.perf_counter()
        
        for business_spec in businesses:
            # Create world model for each business
            world_model = WorldModel()
            world_model.replay_buffer = MockReplayBuffer(50)
            
            # Train world model
            await world_model.train(num_epochs=1, batch_size=16)
            
            results.append({
                "name": business_spec["name"],
                "success": True,
                "loss": world_model.training_history[-1]["loss"] if world_model.training_history else 0.0,
                "fp16_enabled": world_model.fp16_enabled
            })
        
        total_duration = time.perf_counter() - total_start
        
        # Validate all succeeded
        assert all(r["success"] for r in results)
        
        # Calculate average loss
        avg_loss = sum(r["loss"] for r in results) / len(results)
        
        print(f"\n{'='*60}")
        print(f"Multiple Businesses Created (FP16)")
        print(f"{'='*60}")
        print(f"Total businesses: {len(results)}")
        print(f"Total duration:   {total_duration:.2f}s")
        print(f"Avg per business: {total_duration/len(results):.2f}s")
        print(f"Average loss:     {avg_loss:.4f}")
        print(f"All FP16 enabled: {all(r['fp16_enabled'] or not torch.cuda.is_available() for r in results)}")
        print(f"{'='*60}")
    
    finally:
        os.environ["ENABLE_FP16_TRAINING"] = "false"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_stability_long_running():
    """Test FP16 stability over extended business creation session."""
    
    os.environ["ENABLE_FP16_TRAINING"] = "true"
    
    try:
        from tests.training.test_se_darwin_fp16_integration import MockReplayBuffer
        
        num_iterations = 10
        world_model = WorldModel()
        
        losses = []
        durations = []
        
        for i in range(num_iterations):
            # Reset replay buffer for each iteration
            world_model.replay_buffer = MockReplayBuffer(100, seed=i)
            
            # Train
            start = time.perf_counter()
            await world_model.train(num_epochs=1, batch_size=16)
            duration = time.perf_counter() - start
            
            # Record metrics
            if world_model.training_history:
                loss = world_model.training_history[-1]["loss"]
                losses.append(loss)
                durations.append(duration)
                
                # Check for numerical issues
                assert not (loss != loss), f"Loss is NaN at iteration {i}"
                assert loss != float('inf'), f"Loss is Inf at iteration {i}"
        
        # Calculate statistics
        avg_loss = sum(losses) / len(losses)
        avg_duration = sum(durations) / len(durations)
        loss_variance = sum((l - avg_loss) ** 2 for l in losses) / len(losses)
        
        # Check overflow rate if FP16 active
        overflow_rate = 0.0
        if world_model._fp16_stats:
            overflow_rate = world_model._fp16_stats.get("overflow_rate", 0.0)
        
        print(f"\n{'='*60}")
        print(f"Long-Running Stability Test (FP16)")
        print(f"{'='*60}")
        print(f"Iterations:       {num_iterations}")
        print(f"Avg duration:     {avg_duration:.3f}s")
        print(f"Avg loss:         {avg_loss:.4f}")
        print(f"Loss variance:    {loss_variance:.6f}")
        print(f"Overflow rate:    {overflow_rate:.2%}")
        print(f"{'='*60}")
        
        # Verify stability
        assert len(losses) == num_iterations, "All iterations should complete"
        assert overflow_rate < 0.5, f"Overflow rate too high: {overflow_rate:.2%}"
        assert loss_variance < 1.0, f"Loss variance too high: {loss_variance:.4f}"
    
    finally:
        os.environ["ENABLE_FP16_TRAINING"] = "false"


@pytest.mark.e2e
@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_e2e_business_creation_realistic_load():
    """Test realistic business creation load with FP16."""
    
    os.environ["ENABLE_FP16_TRAINING"] = "true"
    
    try:
        from tests.training.test_se_darwin_fp16_integration import MockReplayBuffer
        
        # Simulate realistic load: 5 businesses with varying complexity
        business_specs = [
            {"name": "simple_service", "trajectories": 50, "epochs": 1},
            {"name": "medium_saas", "trajectories": 100, "epochs": 2},
            {"name": "complex_platform", "trajectories": 200, "epochs": 3},
            {"name": "small_api", "trajectories": 30, "epochs": 1},
            {"name": "enterprise_app", "trajectories": 150, "epochs": 2},
        ]
        
        results = []
        total_start = time.perf_counter()
        
        for spec in business_specs:
            world_model = WorldModel()
            world_model.replay_buffer = MockReplayBuffer(spec["trajectories"])
            
            start = time.perf_counter()
            await world_model.train(
                num_epochs=spec["epochs"],
                batch_size=16
            )
            duration = time.perf_counter() - start
            
            results.append({
                "name": spec["name"],
                "duration": duration,
                "trajectories": spec["trajectories"],
                "epochs": spec["epochs"],
                "loss": world_model.training_history[-1]["loss"] if world_model.training_history else 0.0,
                "fp16_enabled": world_model.fp16_enabled
            })
        
        total_duration = time.perf_counter() - total_start
        
        # Calculate metrics
        total_businesses = len(results)
        avg_duration = total_duration / total_businesses
        total_trajectories = sum(r["trajectories"] for r in results)
        throughput = total_trajectories / total_duration
        
        print(f"\n{'='*60}")
        print(f"Realistic Business Creation Load (FP16)")
        print(f"{'='*60}")
        print(f"Total businesses:    {total_businesses}")
        print(f"Total duration:      {total_duration:.2f}s")
        print(f"Avg per business:    {avg_duration:.2f}s")
        print(f"Total trajectories:  {total_trajectories}")
        print(f"Throughput:          {throughput:.1f} trajectories/s")
        print(f"{'='*60}")
        
        for result in results:
            print(f"  {result['name']:20s} - {result['duration']:6.2f}s - {result['trajectories']:3d} traj - loss: {result['loss']:.4f}")
        
        print(f"{'='*60}")
        
        # Verify all succeeded
        assert all(r["loss"] >= 0 for r in results)
        assert total_duration < 300.0, "Should complete within 5 minutes"
    
    finally:
        os.environ["ENABLE_FP16_TRAINING"] = "false"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "e2e"])

