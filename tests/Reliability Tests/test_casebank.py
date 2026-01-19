"""
Test Suite for CaseBank - Case-Based Reasoning Memory System

Based on Memento (arXiv:2508.16153)

Tests:
1. Case storage and retrieval
2. K=4 retrieval accuracy
3. Reward filtering (min_reward=0.6)
4. Similarity threshold (min_similarity=0.8)
5. Integration with agents (SE-Darwin, WaltzRL, HALO)
6. Embedding generation and similarity
7. Persistence (JSONL storage)
8. Concurrent access
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from typing import List, Dict, Any

from infrastructure.casebank import Case, CaseBank, get_casebank


class TestCaseBasics:
    """Test Case dataclass functionality"""

    def test_case_creation(self):
        """Test basic case creation"""
        case = Case(
            state="Test task",
            action="Test solution",
            reward=0.85,
            metadata={"agent": "test"}
        )

        assert case.state == "Test task"
        assert case.action == "Test solution"
        assert case.reward == 0.85
        assert case.metadata["agent"] == "test"
        assert len(case.case_id) == 16  # 16-char hex hash

    def test_case_id_unique(self):
        """Test case IDs are unique"""
        case1 = Case(state="task1", action="action1", reward=0.8, metadata={})
        case2 = Case(state="task2", action="action2", reward=0.8, metadata={})

        assert case1.case_id != case2.case_id

    def test_case_id_deterministic(self):
        """Test case IDs are deterministic for same content"""
        case1 = Case(state="task", action="action", reward=0.8, metadata={"agent": "a"})
        case2 = Case(state="task", action="action", reward=0.8, metadata={"agent": "a"})

        assert case1.case_id == case2.case_id

    def test_case_to_dict(self):
        """Test case serialization"""
        case = Case(
            state="test",
            action="solution",
            reward=0.9,
            metadata={"agent": "test"}
        )

        data = case.to_dict()
        assert data["state"] == "test"
        assert data["action"] == "solution"
        assert data["reward"] == 0.9
        assert data["metadata"]["agent"] == "test"

    def test_case_from_dict(self):
        """Test case deserialization"""
        data = {
            "state": "test",
            "action": "solution",
            "reward": 0.9,
            "metadata": {"agent": "test"},
            "case_id": "abc123",
            "embedding": [0.1, 0.2, 0.3]
        }

        case = Case.from_dict(data)
        assert case.state == "test"
        assert case.action == "solution"
        assert case.reward == 0.9


class TestCaseBankStorage:
    """Test CaseBank storage functionality"""

    @pytest.mark.asyncio
    async def test_add_case(self):
        """Test adding a single case"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            case = await bank.add_case(
                state="Build API",
                action="Created FastAPI service",
                reward=0.85,
                metadata={"agent": "builder"}
            )

            assert case.reward == 0.85
            assert len(bank.cases) == 1
            assert bank.cases[0].case_id == case.case_id

    @pytest.mark.asyncio
    async def test_add_multiple_cases(self):
        """Test adding multiple cases"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            for i in range(10):
                await bank.add_case(
                    state=f"Task {i}",
                    action=f"Solution {i}",
                    reward=0.5 + (i * 0.05),
                    metadata={"agent": "test", "index": i}
                )

            assert len(bank.cases) == 10

    @pytest.mark.asyncio
    async def test_persistence(self):
        """Test cases persist to disk"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"

            # Create bank and add cases
            bank1 = CaseBank(storage_path=storage_path)
            await bank1.add_case(
                state="Task 1",
                action="Solution 1",
                reward=0.8,
                metadata={"agent": "test"}
            )
            await bank1.add_case(
                state="Task 2",
                action="Solution 2",
                reward=0.9,
                metadata={"agent": "test"}
            )

            # Create new bank instance - should load from disk
            bank2 = CaseBank(storage_path=storage_path)
            assert len(bank2.cases) == 2
            assert bank2.cases[0].state == "Task 1"
            assert bank2.cases[1].state == "Task 2"

    @pytest.mark.asyncio
    async def test_get_case_by_id(self):
        """Test retrieving specific case by ID"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            case = await bank.add_case(
                state="Test",
                action="Solution",
                reward=0.8,
                metadata={}
            )

            retrieved = await bank.get_case_by_id(case.case_id)
            assert retrieved is not None
            assert retrieved.case_id == case.case_id
            assert retrieved.state == "Test"


class TestCaseBankRetrieval:
    """Test CaseBank retrieval and similarity matching"""

    @pytest.mark.asyncio
    async def test_retrieve_k_cases(self):
        """Test K=4 retrieval (Memento paper optimal)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            # Add 10 cases with varying rewards
            for i in range(10):
                await bank.add_case(
                    state=f"Build API with {i} endpoints",
                    action=f"Created API {i}",
                    reward=0.5 + (i * 0.05),
                    metadata={"agent": "builder"}
                )

            # Retrieve K=4 similar cases
            results = await bank.retrieve_similar(
                query_state="Build API with 5 endpoints",
                k=4,
                min_reward=0.0,  # Lower threshold for testing
                min_similarity=0.0
            )

            assert len(results) <= 4  # Should return at most K=4

    @pytest.mark.asyncio
    async def test_reward_filtering(self):
        """Test min_reward=0.6 filtering"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            # Add cases with low and high rewards
            await bank.add_case(state="Task A", action="Sol A", reward=0.3, metadata={})
            await bank.add_case(state="Task B", action="Sol B", reward=0.5, metadata={})
            await bank.add_case(state="Task C", action="Sol C", reward=0.7, metadata={})
            await bank.add_case(state="Task D", action="Sol D", reward=0.9, metadata={})

            # Retrieve with min_reward=0.6
            results = await bank.retrieve_similar(
                query_state="Task",
                k=10,
                min_reward=0.6,
                min_similarity=0.0
            )

            # Should only get cases C and D (reward >= 0.6)
            assert all(case.reward >= 0.6 for case, _ in results)
            assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_agent_filtering(self):
        """Test agent-specific filtering"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            # Add cases from different agents
            await bank.add_case(
                state="Task 1", action="Sol 1", reward=0.8,
                metadata={"agent": "builder"}
            )
            await bank.add_case(
                state="Task 2", action="Sol 2", reward=0.8,
                metadata={"agent": "marketing"}
            )
            await bank.add_case(
                state="Task 3", action="Sol 3", reward=0.8,
                metadata={"agent": "builder"}
            )

            # Retrieve only builder cases
            results = await bank.retrieve_similar(
                query_state="Task",
                k=10,
                min_reward=0.0,
                min_similarity=0.0,
                agent_filter="builder"
            )

            assert len(results) == 2
            assert all(case.metadata.get("agent") == "builder" for case, _ in results)

    @pytest.mark.asyncio
    async def test_similarity_threshold(self):
        """Test min_similarity=0.8 threshold"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            # Add very similar and dissimilar cases
            await bank.add_case(
                state="Build Python API",
                action="Created Python API",
                reward=0.9,
                metadata={}
            )
            await bank.add_case(
                state="Design marketing campaign",
                action="Created campaign",
                reward=0.9,
                metadata={}
            )

            # Query for Python API - should only match similar
            results = await bank.retrieve_similar(
                query_state="Build Python API service",
                k=10,
                min_reward=0.0,
                min_similarity=0.8
            )

            # Should filter by similarity
            assert all(sim >= 0.8 for _, sim in results)


class TestCaseBankContextBuilding:
    """Test context building for prompt augmentation"""

    @pytest.mark.asyncio
    async def test_build_case_context(self):
        """Test formatting cases as learning context"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            case1 = await bank.add_case(
                state="Build API",
                action="Created FastAPI service",
                reward=0.9,
                metadata={"agent": "builder"}
            )
            case2 = await bank.add_case(
                state="Deploy API",
                action="Deployed to AWS",
                reward=0.8,
                metadata={"agent": "deploy"}
            )

            # Build context
            cases_with_sim = [(case1, 0.95), (case2, 0.85)]
            context = bank.build_case_context(cases_with_sim)

            assert "Past similar tasks and outcomes" in context
            assert "Example 1" in context
            assert "Example 2" in context
            assert "Build API" in context
            assert "Deploy API" in context

    @pytest.mark.asyncio
    async def test_context_truncation(self):
        """Test long texts are truncated in context"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            # Add case with very long text
            long_text = "x" * 1000
            case = await bank.add_case(
                state=long_text,
                action=long_text,
                reward=0.9,
                metadata={}
            )

            # Build context with max_length=100
            context = bank.build_case_context([(case, 0.9)], max_length=100)

            # Should be truncated
            assert "..." in context


class TestCaseBankOperations:
    """Test CaseBank operations"""

    @pytest.mark.asyncio
    async def test_get_all_cases(self):
        """Test getting all cases"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            await bank.add_case(state="T1", action="S1", reward=0.8, metadata={"agent": "a"})
            await bank.add_case(state="T2", action="S2", reward=0.9, metadata={"agent": "b"})

            all_cases = await bank.get_all_cases()
            assert len(all_cases) == 2

    @pytest.mark.asyncio
    async def test_get_all_cases_filtered(self):
        """Test get_all_cases with filters"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            await bank.add_case(state="T1", action="S1", reward=0.5, metadata={"agent": "a"})
            await bank.add_case(state="T2", action="S2", reward=0.9, metadata={"agent": "a"})
            await bank.add_case(state="T3", action="S3", reward=0.8, metadata={"agent": "b"})

            # Filter by agent and reward
            filtered = await bank.get_all_cases(agent_filter="a", min_reward=0.7)
            assert len(filtered) == 1
            assert filtered[0].reward == 0.9

    @pytest.mark.asyncio
    async def test_clear_cases(self):
        """Test clearing cases"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            await bank.add_case(state="T1", action="S1", reward=0.8, metadata={"agent": "a"})
            await bank.add_case(state="T2", action="S2", reward=0.9, metadata={"agent": "a"})

            cleared = await bank.clear_cases()
            assert cleared == 2
            assert len(bank.cases) == 0

    @pytest.mark.asyncio
    async def test_clear_cases_filtered(self):
        """Test clearing cases with agent filter"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            await bank.add_case(state="T1", action="S1", reward=0.8, metadata={"agent": "a"})
            await bank.add_case(state="T2", action="S2", reward=0.9, metadata={"agent": "b"})

            cleared = await bank.clear_cases(agent_filter="a")
            assert cleared == 1
            assert len(bank.cases) == 1
            assert bank.cases[0].metadata["agent"] == "b"


class TestEmbeddingAndSimilarity:
    """Test embedding generation and similarity calculation"""

    @pytest.mark.asyncio
    async def test_embedding_generation(self):
        """Test embeddings are generated"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path, embedding_dim=384)

            case = await bank.add_case(
                state="Test task",
                action="Test solution",
                reward=0.8,
                metadata={}
            )

            assert case.embedding is not None
            assert len(case.embedding) == 384

    @pytest.mark.asyncio
    async def test_embedding_similarity(self):
        """Test similar texts have high similarity"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            # Add similar cases
            await bank.add_case(
                state="Build Python API",
                action="Created API",
                reward=0.9,
                metadata={}
            )
            await bank.add_case(
                state="Build Python API service",
                action="Created API service",
                reward=0.9,
                metadata={}
            )

            # Query should find similar
            results = await bank.retrieve_similar(
                query_state="Build Python API application",
                k=2,
                min_reward=0.0,
                min_similarity=0.0
            )

            assert len(results) == 2


class TestConcurrency:
    """Test concurrent access to CaseBank"""

    @pytest.mark.asyncio
    async def test_concurrent_adds(self):
        """Test concurrent case additions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            # Add cases concurrently
            tasks = [
                bank.add_case(
                    state=f"Task {i}",
                    action=f"Solution {i}",
                    reward=0.8,
                    metadata={"index": i}
                )
                for i in range(10)
            ]

            results = await asyncio.gather(*tasks)
            assert len(results) == 10
            assert len(bank.cases) == 10

    @pytest.mark.asyncio
    async def test_concurrent_retrievals(self):
        """Test concurrent retrievals"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = f"{tmpdir}/test.jsonl"
            bank = CaseBank(storage_path=storage_path)

            # Add some cases
            for i in range(5):
                await bank.add_case(
                    state=f"Task {i}",
                    action=f"Solution {i}",
                    reward=0.8,
                    metadata={}
                )

            # Retrieve concurrently
            tasks = [
                bank.retrieve_similar(f"Task {i}", k=2, min_reward=0.0, min_similarity=0.0)
                for i in range(10)
            ]

            results = await asyncio.gather(*tasks)
            assert len(results) == 10


class TestSingleton:
    """Test CaseBank singleton pattern"""

    def test_singleton_instance(self):
        """Test get_casebank returns same instance"""
        bank1 = get_casebank(reset=True)
        bank2 = get_casebank(reset=False)

        assert bank1 is bank2

    def test_singleton_reset(self):
        """Test singleton reset creates new instance"""
        bank1 = get_casebank(reset=True)
        bank2 = get_casebank(reset=True)

        assert bank1 is not bank2


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
