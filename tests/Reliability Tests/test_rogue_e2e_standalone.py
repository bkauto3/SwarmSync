"""
Standalone E2E Integration Tests for ROGUE (no external services required).

These tests validate ROGUE functionality without requiring A2A service or external dependencies.
"""

import pytest
from pathlib import Path
from infrastructure.testing.scenario_loader import ScenarioLoader
from infrastructure.testing.rogue_runner import CostTracker, ResultCache


class TestROGUEStandaloneE2E:
    """Standalone E2E tests that don't require external services."""
    
    def test_scenario_loading_all_files(self):
        """Test loading all scenario files."""
        loader = ScenarioLoader(strict=False)  # Use non-strict for flexibility
        scenario_dir = Path("tests/rogue/scenarios")
        
        if not scenario_dir.exists():
            pytest.skip("Scenario directory not found")
        
        yaml_files = list(scenario_dir.glob("*.yaml"))
        assert len(yaml_files) > 0, "No scenario files found"
        
        total_scenarios = 0
        for yaml_file in yaml_files:
            try:
                scenarios = loader.load_from_yaml(str(yaml_file))
                total_scenarios += len(scenarios)
            except Exception as e:
                pytest.fail(f"Failed to load {yaml_file}: {e}")
        
        # Should have loaded 1,500+ scenarios
        assert total_scenarios >= 1500, f"Expected 1500+ scenarios, got {total_scenarios}"
        print(f"✅ Successfully loaded {total_scenarios} scenarios from {len(yaml_files)} files")
    
    def test_cost_estimation_accuracy(self):
        """Test cost estimation for different priorities."""
        tracker = CostTracker()

        # P0: GPT-4o (expensive)
        p0_cost = tracker.estimate_cost("P0", actual_tokens={"input": 500, "output": 200})

        # P2: Gemini Flash (cheap)
        p2_cost = tracker.estimate_cost("P2", actual_tokens={"input": 500, "output": 200})

        summary = tracker.get_summary()

        # P0 should be significantly more expensive than P2
        assert p0_cost > p2_cost * 10, "P0 should be much more expensive than P2"
        print(f"✅ P0 cost: ${p0_cost:.6f}, P2 cost: ${p2_cost:.6f}")
        print(f"   Total cost: ${summary['total_cost_usd']:.6f}")
    
    def test_full_scenario_statistics(self):
        """Test statistics across all scenarios."""
        loader = ScenarioLoader()
        scenario_dir = Path("tests/rogue/scenarios")
        
        if not scenario_dir.exists():
            pytest.skip("Scenario directory not found")
        
        yaml_files = list(scenario_dir.glob("*.yaml"))
        all_scenarios = []
        
        for yaml_file in yaml_files:
            try:
                scenarios = loader.load_from_yaml(str(yaml_file))
                all_scenarios.extend(scenarios)
            except Exception:
                pass  # Skip invalid files
        
        # Get statistics
        stats = loader.get_statistics(all_scenarios)
        
        assert stats["total"] >= 1500
        assert "P0" in stats["by_priority"]
        assert "P1" in stats["by_priority"]
        assert "P2" in stats["by_priority"]
        
        # Verify distribution
        assert stats["by_priority"]["P0"] >= 500
        assert stats["by_priority"]["P1"] >= 700
        assert stats["by_priority"]["P2"] >= 300
        
        print(f"✅ Total scenarios: {stats['total']}")
        print(f"   P0: {stats['by_priority']['P0']}")
        print(f"   P1: {stats['by_priority']['P1']}")
        print(f"   P2: {stats['by_priority']['P2']}")
    
    def test_scenario_filtering_by_priority(self):
        """Test filtering scenarios by priority."""
        loader = ScenarioLoader()
        scenario_dir = Path("tests/rogue/scenarios")
        
        if not scenario_dir.exists():
            pytest.skip("Scenario directory not found")
        
        # Load all scenarios
        yaml_files = list(scenario_dir.glob("*.yaml"))
        all_scenarios = []
        
        for yaml_file in yaml_files:
            try:
                scenarios = loader.load_from_yaml(str(yaml_file))
                all_scenarios.extend(scenarios)
            except Exception:
                pass
        
        # Filter by P0
        p0_scenarios = loader.filter_by_priority(all_scenarios, "P0")
        assert len(p0_scenarios) >= 500
        assert all(s.get("priority") == "P0" for s in p0_scenarios)
        
        # Filter by P1
        p1_scenarios = loader.filter_by_priority(all_scenarios, "P1")
        assert len(p1_scenarios) >= 700
        assert all(s.get("priority") == "P1" for s in p1_scenarios)
        
        # Filter by P2
        p2_scenarios = loader.filter_by_priority(all_scenarios, "P2")
        assert len(p2_scenarios) >= 300
        assert all(s.get("priority") == "P2" for s in p2_scenarios)
        
        print(f"✅ Filtered P0: {len(p0_scenarios)}, P1: {len(p1_scenarios)}, P2: {len(p2_scenarios)}")
    
    def test_scenario_filtering_by_category(self):
        """Test filtering scenarios by category."""
        loader = ScenarioLoader()
        scenario_dir = Path("tests/rogue/scenarios")
        
        if not scenario_dir.exists():
            pytest.skip("Scenario directory not found")
        
        # Load all scenarios
        yaml_files = list(scenario_dir.glob("*.yaml"))
        all_scenarios = []
        
        for yaml_file in yaml_files:
            try:
                scenarios = loader.load_from_yaml(str(yaml_file))
                all_scenarios.extend(scenarios)
            except Exception:
                pass
        
        # Filter by category
        success_scenarios = loader.filter_by_category(all_scenarios, "success")
        assert len(success_scenarios) > 0
        assert all(s.get("category") == "success" for s in success_scenarios)
        
        print(f"✅ Filtered 'success' category: {len(success_scenarios)} scenarios")
    
    def test_result_cache_performance(self):
        """Test result cache performance."""
        cache = ResultCache()

        # Create test scenarios
        scenarios = []
        for i in range(100):
            scenario = {
                "id": f"cache_test_{i:03d}",
                "input": {"task": f"Test task {i}"},
                "expected_output": {"status": "success"}
            }
            scenarios.append(scenario)

        # First pass - all cache misses
        for scenario in scenarios:
            scenario_id = scenario["id"]
            result = cache.get(scenario_id, scenario)
            assert result is None
            cache.put(scenario_id, scenario, {"status": "success", "score": 0.9})

        # Second pass - all cache hits
        for scenario in scenarios:
            scenario_id = scenario["id"]
            result = cache.get(scenario_id, scenario)
            assert result is not None
            assert result["status"] == "success"

        # Verify cache stats
        stats = cache.get_stats()
        assert stats["hits"] == 100
        assert stats["misses"] == 100
        assert stats["hit_rate"] == 0.5

        print(f"✅ Cache performance: {stats['hits']} hits, {stats['misses']} misses, {stats['hit_rate']:.1%} hit rate")
    
    def test_cost_tracking_for_full_run(self):
        """Test cost tracking for a full 1,500 scenario run."""
        tracker = CostTracker()

        # Simulate 1,500 scenarios
        # P0: 500 scenarios
        for _ in range(500):
            tracker.estimate_cost("P0", actual_tokens={"input": 500, "output": 200})

        # P1: 700 scenarios
        for _ in range(700):
            tracker.estimate_cost("P1", actual_tokens={"input": 500, "output": 200})

        # P2: 300 scenarios
        for _ in range(300):
            tracker.estimate_cost("P2", actual_tokens={"input": 500, "output": 200})

        summary = tracker.get_summary()

        total_cost = summary["total_cost_usd"]
        assert total_cost > 0

        # P0 should dominate the cost (both P0 and P1 use GPT-4o)
        p0_cost = summary["cost_by_priority"]["P0"]
        p1_cost = summary["cost_by_priority"]["P1"]
        p2_cost = summary["cost_by_priority"]["P2"]

        # P0 + P1 should be much more expensive than P2
        assert (p0_cost + p1_cost) > p2_cost * 10, "GPT-4o scenarios should dominate cost"

        print(f"✅ Full run cost estimate:")
        print(f"   Total cost: ${total_cost:.4f}")
        print(f"   P0 cost: ${p0_cost:.4f} ({p0_cost/total_cost:.1%})")
        print(f"   P1 cost: ${p1_cost:.4f} ({p1_cost/total_cost:.1%})")
        print(f"   P2 cost: ${p2_cost:.4f} ({p2_cost/total_cost:.1%})")
        print(f"   Estimated monthly: ${summary['estimated_monthly_cost']:.2f}")
    
    def test_scenario_validation_strict_mode(self):
        """Test scenario validation in strict mode."""
        loader = ScenarioLoader(strict=True)
        
        # Valid scenario
        valid_scenario = {
            "id": "valid_001",
            "priority": "P1",
            "category": "success",
            "description": "Test scenario",
            "input": {"task": "Test task"},
            "expected_output": {"status": "success"}
        }
        
        # This should not raise an error
        try:
            loader._validate_scenario(valid_scenario)
            print("✅ Valid scenario passed strict validation")
        except Exception as e:
            pytest.fail(f"Valid scenario failed validation: {e}")
    
    def test_scenario_count_by_agent(self):
        """Test scenario count per agent."""
        loader = ScenarioLoader()
        scenario_dir = Path("tests/rogue/scenarios")
        
        if not scenario_dir.exists():
            pytest.skip("Scenario directory not found")
        
        # Count scenarios per agent
        agent_counts = {}
        
        for yaml_file in scenario_dir.glob("*_agent_*.yaml"):
            try:
                scenarios = loader.load_from_yaml(str(yaml_file))
                agent_name = yaml_file.stem.split("_p")[0]  # Extract agent name
                
                if agent_name not in agent_counts:
                    agent_counts[agent_name] = 0
                agent_counts[agent_name] += len(scenarios)
            except Exception:
                pass
        
        # Each agent should have scenarios
        assert len(agent_counts) >= 15, f"Expected 15+ agents, got {len(agent_counts)}"
        
        print(f"✅ Scenario distribution across {len(agent_counts)} agents:")
        for agent, count in sorted(agent_counts.items()):
            print(f"   {agent}: {count} scenarios")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

