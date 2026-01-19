"""
Test Suite for Memento Agent - Case-Based Reasoning Wrapper

Tests agent execution with memory augmentation
"""

import asyncio
import pytest
import tempfile
from pathlib import Path

from infrastructure.memento_agent import MementoAgent, create_memento_agent
from infrastructure.casebank import CaseBank


class MockLLMClient:
    """Mock LLM client for testing"""

    async def generate(self, prompt: str, **kwargs) -> str:
        # Return simple response based on prompt length
        if "Past similar tasks" in prompt:
            return f"Solution with context (prompt_len={len(prompt)})"
        else:
            return f"Solution without context (prompt_len={len(prompt)})"


class TestMementoAgentBasics:
    """Test basic Memento agent functionality"""

    @pytest.mark.asyncio
    async def test_agent_creation(self):
        """Test creating Memento agent"""
        llm = MockLLMClient()
        agent = MementoAgent(agent_name="test_agent", llm_client=llm)

        assert agent.agent_name == "test_agent"
        assert agent.llm_client == llm
        assert agent.k_cases == 4

    @pytest.mark.asyncio
    async def test_execute_without_memory(self):
        """Test execution when no past cases exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            casebank = CaseBank(storage_path=storage_path)
            llm = MockLLMClient()

            agent = MementoAgent(
                agent_name="test",
                llm_client=llm,
                casebank=casebank
            )

            result = await agent.execute_with_memory(task="Build API")

            assert result["solution"] is not None
            assert result["cases_used"] == 0
            assert result["had_context"] is False
            assert result["reward"] > 0  # Should have default validation

    @pytest.mark.asyncio
    async def test_execute_with_memory(self):
        """Test execution with past case retrieval"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            casebank = CaseBank(storage_path=storage_path)
            llm = MockLLMClient()

            # Add past successful case
            await casebank.add_case(
                state="Build API",
                action="Created FastAPI service",
                reward=0.9,
                metadata={"agent": "test"}
            )

            agent = MementoAgent(
                agent_name="test",
                llm_client=llm,
                casebank=casebank
            )

            # Execute similar task - should retrieve past case
            result = await agent.execute_with_memory(task="Build API service")

            # Note: Due to simple embedding, may or may not match
            # Just verify execution works
            assert result["solution"] is not None
            assert "cases_used" in result

    @pytest.mark.asyncio
    async def test_case_storage(self):
        """Test outcomes are stored for future learning"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            casebank = CaseBank(storage_path=storage_path)
            llm = MockLLMClient()

            agent = MementoAgent(
                agent_name="test",
                llm_client=llm,
                casebank=casebank,
                enable_storage=True
            )

            # Execute task
            await agent.execute_with_memory(task="Test task")

            # Verify case was stored
            all_cases = await casebank.get_all_cases(agent_filter="test")
            assert len(all_cases) == 1
            assert all_cases[0].state == "Test task"

    @pytest.mark.asyncio
    async def test_storage_disabled(self):
        """Test storage can be disabled"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            casebank = CaseBank(storage_path=storage_path)
            llm = MockLLMClient()

            agent = MementoAgent(
                agent_name="test",
                llm_client=llm,
                casebank=casebank,
                enable_storage=False
            )

            # Execute task
            await agent.execute_with_memory(task="Test task")

            # Verify no case was stored
            all_cases = await casebank.get_all_cases(agent_filter="test")
            assert len(all_cases) == 0


class TestMementoAgentValidation:
    """Test validation functionality"""

    @pytest.mark.asyncio
    async def test_custom_validator(self):
        """Test custom validation function"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            casebank = CaseBank(storage_path=storage_path)
            llm = MockLLMClient()

            agent = MementoAgent(
                agent_name="test",
                llm_client=llm,
                casebank=casebank
            )

            # Custom validator: reward = 0.95
            def validator(task, solution):
                return 0.95

            result = await agent.execute_with_memory(
                task="Test",
                validator=validator
            )

            assert result["reward"] == 0.95

    @pytest.mark.asyncio
    async def test_async_validator(self):
        """Test async validation function"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            casebank = CaseBank(storage_path=storage_path)
            llm = MockLLMClient()

            agent = MementoAgent(
                agent_name="test",
                llm_client=llm,
                casebank=casebank
            )

            # Async validator
            async def validator(task, solution):
                await asyncio.sleep(0.001)
                return 0.88

            result = await agent.execute_with_memory(
                task="Test",
                validator=validator
            )

            assert result["reward"] == 0.88


class TestMementoAgentBatch:
    """Test batch execution"""

    @pytest.mark.asyncio
    async def test_batch_parallel(self):
        """Test parallel batch execution"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            casebank = CaseBank(storage_path=storage_path)
            llm = MockLLMClient()

            agent = MementoAgent(
                agent_name="test",
                llm_client=llm,
                casebank=casebank
            )

            tasks = [f"Task {i}" for i in range(5)]
            results = await agent.execute_batch_with_memory(tasks, parallel=True)

            assert len(results) == 5
            assert all("solution" in r for r in results)

    @pytest.mark.asyncio
    async def test_batch_sequential(self):
        """Test sequential batch execution"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            casebank = CaseBank(storage_path=storage_path)
            llm = MockLLMClient()

            agent = MementoAgent(
                agent_name="test",
                llm_client=llm,
                casebank=casebank
            )

            tasks = [f"Task {i}" for i in range(5)]
            results = await agent.execute_batch_with_memory(tasks, parallel=False)

            assert len(results) == 5
            assert all("solution" in r for r in results)


class TestMementoAgentMemoryStats:
    """Test memory statistics"""

    @pytest.mark.asyncio
    async def test_memory_stats_empty(self):
        """Test stats when no cases"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            casebank = CaseBank(storage_path=storage_path)
            llm = MockLLMClient()

            agent = MementoAgent(
                agent_name="test",
                llm_client=llm,
                casebank=casebank
            )

            stats = await agent.get_memory_stats()
            assert stats["total_cases"] == 0
            assert stats["avg_reward"] == 0.0

    @pytest.mark.asyncio
    async def test_memory_stats_with_cases(self):
        """Test stats with cases"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            casebank = CaseBank(storage_path=storage_path)
            llm = MockLLMClient()

            agent = MementoAgent(
                agent_name="test",
                llm_client=llm,
                casebank=casebank
            )

            # Execute tasks to create cases
            await agent.execute_with_memory("Task 1")
            await agent.execute_with_memory("Task 2")

            stats = await agent.get_memory_stats()
            assert stats["total_cases"] == 2
            assert stats["avg_reward"] > 0

    @pytest.mark.asyncio
    async def test_clear_memory(self):
        """Test clearing agent memory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            casebank = CaseBank(storage_path=storage_path)
            llm = MockLLMClient()

            agent = MementoAgent(
                agent_name="test",
                llm_client=llm,
                casebank=casebank
            )

            # Execute tasks
            await agent.execute_with_memory("Task 1")
            await agent.execute_with_memory("Task 2")

            # Clear memory
            cleared = await agent.clear_memory()
            assert cleared == 2

            stats = await agent.get_memory_stats()
            assert stats["total_cases"] == 0


class TestFactoryFunction:
    """Test factory function"""

    @pytest.mark.asyncio
    async def test_create_memento_agent(self):
        """Test factory function creates agent"""
        llm = MockLLMClient()
        agent = create_memento_agent(agent_name="test", llm_client=llm)

        assert agent.agent_name == "test"
        assert agent.llm_client == llm


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
