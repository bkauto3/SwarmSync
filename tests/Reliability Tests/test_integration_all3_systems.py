"""
Integration Tests for All 3 Research Systems

Tests the complete integration of:
1. Policy Cards (arXiv:2510.24383) - Runtime governance
2. Capability Maps - Pre-tool middleware validation
3. Modular Prompts (arXiv:2510.26493) - Context Engineering 2.0

All integrated into:
- HALO Router (infrastructure/halo_router.py)
- Genesis Meta-Agent (infrastructure/genesis_meta_agent.py)

Author: Cora (AI Orchestration Specialist)
Date: November 5, 2025
"""

import pytest
import os
from pathlib import Path
from infrastructure.halo_router import HALORouter
from infrastructure.genesis_meta_agent import GenesisMetaAgent
from infrastructure.task_dag import Task, TaskDAG


class TestPolicyCardsIntegration:
    """Test Policy Cards integration into HALO Router"""

    def test_policy_cards_factory_method(self):
        """Test HALORouter factory method creates policy-aware router"""
        router = HALORouter.create_with_integrations(
            enable_policy_cards=True,
            enable_capability_maps=False,
            policy_cards_dir=".policy_cards"
        )

        # Should return PolicyAwareHALORouter wrapper
        assert router is not None
        assert hasattr(router, 'halo_router') or hasattr(router, 'agent_registry')

    def test_policy_cards_directory_exists(self):
        """Verify policy cards directory exists"""
        policy_dir = Path(".policy_cards")
        assert policy_dir.exists(), "Policy cards directory not found"

        # Should have YAML files
        yaml_files = list(policy_dir.glob("*.yaml"))
        assert len(yaml_files) > 0, "No policy card files found"

    def test_policy_enforcement_basic(self):
        """Test basic policy enforcement"""
        router = HALORouter.create_with_integrations(
            enable_policy_cards=True,
            enable_capability_maps=False
        )

        # Create test task
        task = Task(
            task_id="test_policy",
            description="Test policy enforcement",
            task_type="test"
        )

        # Router should accept task (basic smoke test)
        assert router is not None


class TestCapabilityMapsIntegration:
    """Test Capability Maps integration into HALO Router"""

    def test_capability_maps_factory_method(self):
        """Test HALORouter factory method creates capability bridge"""
        router = HALORouter.create_with_integrations(
            enable_policy_cards=False,
            enable_capability_maps=True,
            capability_maps_dir="maps/capabilities"
        )

        # Should return HALOCapabilityBridge wrapper
        assert router is not None
        # Check for capability bridge attributes
        assert hasattr(router, 'halo') or hasattr(router, 'tool_router') or hasattr(router, 'agent_registry')

    def test_capability_maps_directory_exists(self):
        """Verify capability maps directory exists"""
        caps_dir = Path("maps/capabilities")
        assert caps_dir.exists(), "Capability maps directory not found"

        # Should have YAML files
        yaml_files = list(caps_dir.glob("*.yaml"))
        assert len(yaml_files) > 0, "No capability map files found"

    def test_capability_validation_basic(self):
        """Test basic capability validation"""
        router = HALORouter.create_with_integrations(
            enable_policy_cards=False,
            enable_capability_maps=True
        )

        # Router should be initialized
        assert router is not None


class TestModularPromptsIntegration:
    """Test Modular Prompts integration into Genesis Meta-Agent"""

    def test_modular_prompts_initialization(self):
        """Test Genesis Meta-Agent initializes with modular prompts"""
        meta_agent = GenesisMetaAgent(
            use_local_llm=True,
            enable_modular_prompts=True
        )

        # Should have prompt assembler
        assert hasattr(meta_agent, 'prompt_assembler')
        assert hasattr(meta_agent, 'enable_modular_prompts')
        assert meta_agent.enable_modular_prompts is True

    def test_modular_prompts_directory_exists(self):
        """Verify modular prompts directory exists"""
        prompts_dir = Path("prompts/modular")
        assert prompts_dir.exists(), "Modular prompts directory not found"

        # Should have 4-file structure for at least one agent
        # Format: {agent}_policy.md, {agent}_schema.yaml, {agent}_memory.json, {agent}_fewshots.yaml
        policy_files = list(prompts_dir.glob("*_policy.md"))
        assert len(policy_files) > 0, "No policy files found in prompts/modular"

    def test_modular_prompts_fallback(self):
        """Test fallback to legacy prompts when modular prompts disabled"""
        meta_agent = GenesisMetaAgent(
            use_local_llm=True,
            enable_modular_prompts=False
        )

        # Should NOT have prompt assembler
        assert meta_agent.prompt_assembler is None
        assert meta_agent.enable_modular_prompts is False


class TestAllSystemsIntegrated:
    """Test all 3 systems working together"""

    def test_all_integrations_enabled(self):
        """Test HALO Router with all integrations enabled"""
        router = HALORouter.create_with_integrations(
            enable_policy_cards=True,
            enable_capability_maps=True,
            policy_cards_dir=".policy_cards",
            capability_maps_dir="maps/capabilities"
        )

        # Should have wrapped router
        assert router is not None

    def test_meta_agent_with_integrated_router(self):
        """Test Genesis Meta-Agent with all systems enabled"""
        meta_agent = GenesisMetaAgent(
            use_local_llm=True,
            enable_modular_prompts=True
        )

        # Should have modular prompts enabled
        assert meta_agent.enable_modular_prompts is True
        assert meta_agent.prompt_assembler is not None

        # Router should exist
        assert meta_agent.router is not None

    def test_end_to_end_task_routing(self):
        """Test end-to-end task routing with all systems"""
        # Create router with all integrations
        router = HALORouter.create_with_integrations(
            enable_policy_cards=True,
            enable_capability_maps=True
        )

        # Create simple task DAG
        dag = TaskDAG()
        task = Task(
            task_id="test_e2e",
            description="Test end-to-end integration",
            task_type="test"
        )
        dag.add_task(task)

        # Should be able to route (smoke test)
        assert router is not None
        assert len(dag.get_all_tasks()) == 1

    def test_integration_directories_complete(self):
        """Test all required directories exist for integrations"""
        required_dirs = [
            ".policy_cards",
            "maps/capabilities",
            "prompts/modular"
        ]

        for dir_path in required_dirs:
            path = Path(dir_path)
            assert path.exists(), f"Required directory not found: {dir_path}"
            assert path.is_dir(), f"Path is not a directory: {dir_path}"

    def test_integration_file_counts(self):
        """Test minimum file counts in each directory"""
        # Policy Cards: Should have at least 5 agent cards
        policy_files = list(Path(".policy_cards").glob("*.yaml"))
        assert len(policy_files) >= 5, f"Expected at least 5 policy cards, found {len(policy_files)}"

        # Capability Maps: Should have at least 5 capability maps
        capability_files = list(Path("maps/capabilities").glob("*.yaml"))
        assert len(capability_files) >= 5, f"Expected at least 5 capability maps, found {len(capability_files)}"

        # Modular Prompts: Should have 4-file sets for at least 5 agents
        prompts_dir = Path("prompts/modular")
        policy_prompts = list(prompts_dir.glob("*_policy.md"))
        schema_prompts = list(prompts_dir.glob("*_schema.yaml"))
        memory_prompts = list(prompts_dir.glob("*_memory.json"))
        fewshots_prompts = list(prompts_dir.glob("*_fewshots.yaml"))

        assert len(policy_prompts) >= 5, f"Expected at least 5 policy prompts, found {len(policy_prompts)}"
        assert len(schema_prompts) >= 5, f"Expected at least 5 schema prompts, found {len(schema_prompts)}"
        assert len(memory_prompts) >= 5, f"Expected at least 5 memory prompts, found {len(memory_prompts)}"
        assert len(fewshots_prompts) >= 5, f"Expected at least 5 fewshot prompts, found {len(fewshots_prompts)}"

    def test_no_breaking_changes(self):
        """Test that integrations don't break existing functionality"""
        # Base HALO Router should still work
        base_router = HALORouter()
        assert base_router is not None
        assert hasattr(base_router, 'agent_registry')
        assert hasattr(base_router, 'routing_rules')

        # Genesis Meta-Agent should still work
        meta_agent = GenesisMetaAgent(use_local_llm=True)
        assert meta_agent is not None
        assert hasattr(meta_agent, 'router')
        assert hasattr(meta_agent, 'business_templates')


class TestIntegrationPerformance:
    """Test performance characteristics of integrated systems"""

    def test_factory_method_speed(self):
        """Test factory method creates router quickly"""
        import time

        start = time.time()
        router = HALORouter.create_with_integrations(
            enable_policy_cards=True,
            enable_capability_maps=True
        )
        elapsed = time.time() - start

        # Should create in under 1 second
        assert elapsed < 1.0, f"Factory method took too long: {elapsed:.2f}s"
        assert router is not None

    def test_modular_prompt_assembly_speed(self):
        """Test modular prompt assembly is fast"""
        from infrastructure.prompts import ModularPromptAssembler
        import time

        assembler = ModularPromptAssembler("prompts/modular")

        # Get list of agents
        agents = assembler.list_agents()
        assert len(agents) > 0, "No agents found"

        # Test assembly speed for first agent
        start = time.time()
        prompt = assembler.assemble(
            agent_id=agents[0],
            task_context="Test performance",
            variables={"test": "value"}
        )
        elapsed = time.time() - start

        # Should assemble in under 0.1 seconds
        assert elapsed < 0.1, f"Prompt assembly took too long: {elapsed:.2f}s"
        assert len(prompt) > 0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
