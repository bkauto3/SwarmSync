"""Comprehensive tests for Modular Prompts system

Tests the 4-file split prompt architecture from Context Engineering 2.0
"""

import pytest
import json
import yaml
import tempfile
from pathlib import Path
from datetime import datetime

from infrastructure.prompts.modular_assembler import ModularPromptAssembler


class TestModularPromptAssembler:
    """Test suite for ModularPromptAssembler class"""

    @pytest.fixture
    def assembler(self):
        """Create ModularPromptAssembler instance pointing to real prompts directory"""
        return ModularPromptAssembler(prompts_dir="prompts/modular")

    @pytest.fixture
    def temp_prompts_dir(self):
        """Create temporary directory with minimal test prompts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create minimal test agent prompts
            # Policy
            (tmpdir / "test_agent_policy.md").write_text(
                "# Test Agent\nRole: Test\n\nResponsibilities:\n- Testing"
            )

            # Schema
            schema = {
                "tools": [{"name": "Read", "parameters": {"file_path": "string"}}],
                "outputs": [{"name": "output", "format": "json", "fields": ["result"]}]
            }
            with open(tmpdir / "test_agent_schema.yaml", "w") as f:
                yaml.dump(schema, f)

            # Memory
            memory = {"test_key": "test_value", "created_at": datetime.now().isoformat()}
            with open(tmpdir / "test_agent_memory.json", "w") as f:
                json.dump(memory, f)

            # Fewshots
            fewshots = {"examples": [{"input": "test input", "output": "test output"}]}
            with open(tmpdir / "test_agent_fewshots.yaml", "w") as f:
                yaml.dump(fewshots, f)

            yield tmpdir

    def test_initialization_success(self, assembler):
        """Test successful initialization with existing prompts directory"""
        assert assembler.prompts_dir.exists()
        assert assembler.cache_enabled is True
        assert len(assembler.cache) == 0

    def test_initialization_missing_directory(self):
        """Test initialization fails with missing directory"""
        with pytest.raises(FileNotFoundError):
            ModularPromptAssembler(prompts_dir="/nonexistent/path")

    def test_assemble_qa_agent(self, assembler):
        """Test assembling QA agent prompt"""
        prompt = assembler.assemble("qa_agent")

        assert isinstance(prompt, str)
        assert len(prompt) > 500  # Should be substantial
        assert "QA Agent" in prompt or "qa_agent" in prompt.lower()
        assert "POLICY" in prompt
        assert "SCHEMA" in prompt
        assert "MEMORY" in prompt
        assert "FEW-SHOT" in prompt

    def test_assemble_with_template_variables(self, assembler):
        """Test prompt assembly with Jinja2 template variables"""
        variables = {"business_name": "TestCo", "iteration": 5}
        prompt = assembler.assemble("qa_agent", variables=variables)

        assert isinstance(prompt, str)
        # Variables should be available for templating
        assert len(prompt) > 0

    def test_assemble_with_task_context(self, assembler):
        """Test prompt assembly with task context appended"""
        context = "Run tests for module X and report coverage"
        prompt = assembler.assemble("qa_agent", task_context=context)

        assert context in prompt
        assert "TASK CONTEXT" in prompt

    def test_assemble_selective_sections(self, assembler):
        """Test assembling only selected sections"""
        prompt = assembler.assemble(
            "qa_agent",
            include_sections=["policy", "fewshots"]
        )

        assert isinstance(prompt, str)
        assert "POLICY" in prompt
        assert "FEW-SHOT" in prompt
        # Schema and memory should not appear (or minimally)

    def test_assemble_batch(self, assembler):
        """Test batch assembling multiple agents"""
        agent_ids = ["qa_agent", "support_agent", "builder_agent"]
        prompts = assembler.assemble_batch(agent_ids)

        assert len(prompts) == 3
        for agent_id in agent_ids:
            assert agent_id in prompts
            prompt = prompts[agent_id]
            assert prompt is not None
            assert isinstance(prompt, str)
            assert len(prompt) > 100

    def test_get_schema(self, assembler):
        """Test retrieving schema for agent"""
        schema = assembler.get_schema("qa_agent")

        assert isinstance(schema, dict)
        assert "tools" in schema
        assert "outputs" in schema
        assert len(schema["tools"]) > 0

    def test_get_schema_missing_agent(self, assembler):
        """Test get_schema fails for non-existent agent"""
        with pytest.raises(FileNotFoundError):
            assembler.get_schema("nonexistent_agent")

    def test_get_memory(self, assembler):
        """Test retrieving memory for agent"""
        memory = assembler.get_memory("qa_agent")

        assert isinstance(memory, dict)
        assert len(memory) > 0
        # Should contain test metrics
        assert "last_test_run" in memory or "recent_learnings" in memory

    def test_get_memory_missing_agent(self, assembler):
        """Test get_memory fails for non-existent agent"""
        with pytest.raises(FileNotFoundError):
            assembler.get_memory("nonexistent_agent")

    def test_get_policy(self, assembler):
        """Test retrieving policy for agent"""
        policy = assembler.get_policy("qa_agent")

        assert isinstance(policy, str)
        assert len(policy) > 0
        assert "QA" in policy or "qa" in policy.lower()

    def test_get_fewshots(self, assembler):
        """Test retrieving few-shot examples"""
        fewshots = assembler.get_fewshots("qa_agent")

        assert isinstance(fewshots, dict)
        assert "examples" in fewshots
        assert len(fewshots["examples"]) > 0
        # Each example should have input and output
        for example in fewshots["examples"]:
            assert "input" in example
            assert "output" in example

    def test_update_memory(self, assembler, temp_prompts_dir):
        """Test updating agent memory"""
        temp_assembler = ModularPromptAssembler(prompts_dir=str(temp_prompts_dir))

        # Update memory
        updates = {"new_metric": 42, "new_learning": "Important insight"}
        temp_assembler.update_memory("test_agent", updates)

        # Verify updates were written
        memory = temp_assembler.get_memory("test_agent")
        assert memory["new_metric"] == 42
        assert memory["new_learning"] == "Important insight"
        assert "last_updated" in memory

    def test_update_memory_missing_agent(self, assembler):
        """Test updating memory for non-existent agent fails"""
        with pytest.raises(FileNotFoundError):
            assembler.update_memory("nonexistent_agent", {"key": "value"})

    def test_add_fewshot_example(self, assembler, temp_prompts_dir):
        """Test adding a new few-shot example"""
        temp_assembler = ModularPromptAssembler(prompts_dir=str(temp_prompts_dir))

        initial_count = len(temp_assembler.get_fewshots("test_agent")["examples"])

        # Add example
        temp_assembler.add_fewshot_example(
            "test_agent",
            input_text="new test input",
            output_text="new test output"
        )

        # Verify example was added
        updated_fewshots = temp_assembler.get_fewshots("test_agent")
        assert len(updated_fewshots["examples"]) == initial_count + 1
        assert updated_fewshots["examples"][-1]["input"] == "new test input"

    def test_validate_agent_prompts_valid(self, assembler):
        """Test validation succeeds for complete agent"""
        results = assembler.validate_agent_prompts("qa_agent")

        assert isinstance(results, dict)
        assert all(results.values())  # All should be True
        assert results["policy"] is True
        assert results["schema"] is True
        assert results["memory"] is True
        assert results["fewshots"] is True

    def test_validate_agent_prompts_missing_file(self, temp_prompts_dir):
        """Test validation catches missing files"""
        # Remove schema file
        (temp_prompts_dir / "test_agent_schema.yaml").unlink()

        assembler = ModularPromptAssembler(prompts_dir=str(temp_prompts_dir))
        results = assembler.validate_agent_prompts("test_agent")

        assert results["schema"] is False
        # Others should still be present
        assert results["policy"] is True
        assert results["memory"] is True

    def test_list_agents(self, assembler):
        """Test listing all available agents"""
        agents = assembler.list_agents()

        assert isinstance(agents, list)
        assert len(agents) >= 13  # At least the main agents
        assert "qa_agent" in agents
        assert all(isinstance(a, str) for a in agents)
        # Should be sorted
        assert agents == sorted(agents)

    def test_get_statistics(self, assembler):
        """Test getting statistics about prompts"""
        stats = assembler.get_statistics()

        assert isinstance(stats, dict)
        assert "total_agents" in stats
        assert "total_files" in stats
        assert "agents" in stats
        assert "cache_enabled" in stats
        assert stats["total_agents"] >= 13
        assert stats["total_files"] >= 50  # At least 4 files per 13 agents

    def test_cache_functionality(self, temp_prompts_dir):
        """Test caching of assembled prompts"""
        assembler = ModularPromptAssembler(
            prompts_dir=str(temp_prompts_dir),
            cache_enabled=True
        )

        # First assembly
        prompt1 = assembler.assemble("test_agent")
        assert len(assembler.cache) == 1

        # Second assembly (should use cache)
        prompt2 = assembler.assemble("test_agent")
        assert len(assembler.cache) == 1  # Cache size unchanged
        assert prompt1 == prompt2

    def test_cache_disabled(self, temp_prompts_dir):
        """Test that caching can be disabled"""
        assembler = ModularPromptAssembler(
            prompts_dir=str(temp_prompts_dir),
            cache_enabled=False
        )

        assembler.assemble("test_agent")
        assert len(assembler.cache) == 0  # Cache not used

    def test_invalid_agent_id_format(self, assembler):
        """Test that invalid agent_ids are rejected"""
        with pytest.raises(ValueError):
            assembler.assemble("invalid@agent#id")

        with pytest.raises(ValueError):
            assembler.assemble("")

        with pytest.raises(ValueError):
            assembler.assemble("a" * 200)  # Too long

    def test_prompt_structure_completeness(self, assembler):
        """Test that assembled prompts have all required sections"""
        prompt = assembler.assemble("qa_agent")

        required_markers = [
            "POLICY",
            "SCHEMA",
            "MEMORY",
            "FEW-SHOT",
            "YOUR TASK"
        ]

        for marker in required_markers:
            assert marker in prompt, f"Missing section marker: {marker}"

    def test_prompt_readability(self, assembler):
        """Test that assembled prompts are human-readable"""
        prompt = assembler.assemble("qa_agent")

        # Should have reasonable structure
        lines = prompt.split("\n")
        assert len(lines) > 20  # Substantial content

        # Should have markdown headers
        headers = [l for l in lines if l.startswith("#")]
        assert len(headers) > 5

    def test_all_agents_valid_prompts(self, assembler):
        """Test that all listed agents have valid complete prompts"""
        agents = assembler.list_agents()

        for agent_id in agents:
            # Should be able to validate
            results = assembler.validate_agent_prompts(agent_id)
            assert all(results.values()), f"Agent {agent_id} missing files"

            # Should be able to assemble
            prompt = assembler.assemble(agent_id)
            assert isinstance(prompt, str)
            assert len(prompt) > 100

    def test_concurrent_assembly(self, assembler):
        """Test assembling multiple agents concurrently"""
        import concurrent.futures

        agents = ["qa_agent", "support_agent", "builder_agent"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(assembler.assemble, agent) for agent in agents]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(results) == 3
        assert all(isinstance(r, str) and len(r) > 100 for r in results)

    def test_prompt_determinism(self, assembler):
        """Test that assembling same agent twice produces identical results"""
        prompt1 = assembler.assemble("qa_agent", include_sections=["policy", "memory"])
        prompt2 = assembler.assemble("qa_agent", include_sections=["policy", "memory"])

        # Should be identical (except for timestamp perhaps)
        # Remove timestamps for comparison
        p1_no_ts = "\n".join(l for l in prompt1.split("\n") if "Generated:" not in l)
        p2_no_ts = "\n".join(l for l in prompt2.split("\n") if "Generated:" not in l)

        assert p1_no_ts == p2_no_ts


class TestModularPromptIntegration:
    """Integration tests for modular prompt system"""

    def test_full_workflow(self):
        """Test complete workflow: assemble -> use -> update"""
        assembler = ModularPromptAssembler(prompts_dir="prompts/modular")

        # 1. Assemble initial prompt
        prompt = assembler.assemble("qa_agent")
        assert len(prompt) > 0

        # 2. Get components
        schema = assembler.get_schema("qa_agent")
        memory = assembler.get_memory("qa_agent")
        policy = assembler.get_policy("qa_agent")

        assert schema and memory and policy

        # 3. Validate consistency
        validation = assembler.validate_agent_prompts("qa_agent")
        assert all(validation.values())

    def test_agent_heterogeneity(self):
        """Test that different agents have appropriately different prompts"""
        assembler = ModularPromptAssembler(prompts_dir="prompts/modular")

        qa_prompt = assembler.assemble("qa_agent")
        builder_prompt = assembler.assemble("builder_agent")
        support_prompt = assembler.assemble("support_agent")

        # Prompts should be different
        assert qa_prompt != builder_prompt
        assert builder_prompt != support_prompt
        assert qa_prompt != support_prompt

        # But all should be substantial
        assert len(qa_prompt) > 100
        assert len(builder_prompt) > 100
        assert len(support_prompt) > 100

    def test_prompt_relevance_to_agent_role(self):
        """Test that prompts contain content relevant to agent's role"""
        assembler = ModularPromptAssembler(prompts_dir="prompts/modular")

        qa_prompt = assembler.assemble("qa_agent")
        builder_prompt = assembler.assemble("builder_agent")

        # QA should mention testing, coverage, tests
        qa_lower = qa_prompt.lower()
        assert any(word in qa_lower for word in ["test", "pytest", "coverage"])

        # Builder should mention code, build, generation
        builder_lower = builder_prompt.lower()
        assert any(word in builder_lower for word in ["code", "build", "generate"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
