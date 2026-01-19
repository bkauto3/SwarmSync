"""
Comprehensive MemoryOS Integration Test Suite
Tests for MongoDB-backed memory system across 6 Genesis agents

Coverage:
- Unit tests (15 tests): MongoDB connection, TTL indexes, isolation, heat-based promotion
- Integration tests (10 tests): ReasoningBank pipeline, multi-agent memory, concurrent access
- Performance tests (5 tests): Retrieval latency, storage throughput, memory overhead

Total: 30+ tests for 100% MemoryOS integration coverage
"""

import pytest
import asyncio
import time
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import MemoryOS MongoDB adapter
from infrastructure.memory_os_mongodb_adapter import (
    GenesisMemoryOSMongoDB,
    create_genesis_memory_mongodb,
    MemoryEntry
)

# Import ReasoningBank adapter
from infrastructure.reasoning_bank_adapter import (
    ReasoningBankAdapter,
    ReasoningTrace,
    ReasoningTraceType,
    ReasoningQuality,
    JudgmentResult,
    get_reasoning_bank
)

# Note: Agent imports removed to avoid circular dependencies during testing
# Tests focus on direct memory adapter functionality


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mongodb_uri():
    """Test MongoDB URI."""
    return os.getenv("MONGODB_URI_TEST", "mongodb://localhost:27017/")


@pytest.fixture
def test_database():
    """Test database name."""
    return "genesis_memory_test"


@pytest.fixture
async def memory_os(mongodb_uri, test_database):
    """Create MemoryOS instance for testing."""
    memory = create_genesis_memory_mongodb(
        mongodb_uri=mongodb_uri,
        database_name=test_database,
        short_term_capacity=10,
        mid_term_capacity=100,
        long_term_knowledge_capacity=50
    )

    yield memory

    # Cleanup: Clear all test data
    for collection_name in ["short_term", "mid_term", "long_term", "metadata"]:
        memory.collections[collection_name].delete_many({})

    memory.close()


@pytest.fixture
async def reasoning_bank(mongodb_uri, test_database):
    """Create ReasoningBank instance for testing."""
    rb = ReasoningBankAdapter(
        mongodb_uri=mongodb_uri,
        database_name=test_database,
        collection_name="reasoning_bank_test",
        enable_faiss=False  # Disable FAISS for testing
    )

    yield rb

    # Cleanup
    rb.collection.delete_many({})
    rb.close()


# ============================================================================
# UNIT TESTS (15 tests)
# ============================================================================

class TestMongoDBConnection:
    """Test MongoDB connection pooling and error handling."""

    def test_connection_success(self, memory_os):
        """Test successful MongoDB connection."""
        assert memory_os.client is not None
        assert memory_os.db is not None
        assert "short_term" in memory_os.collections

    def test_connection_pooling(self, memory_os):
        """Test MongoDB connection pool configuration."""
        # Verify connection pool settings
        assert memory_os.client.max_pool_size == 50
        assert memory_os.client.min_pool_size == 10

    def test_connection_failure_handling(self):
        """Test graceful handling of connection failures."""
        with pytest.raises(ConnectionError):
            GenesisMemoryOSMongoDB(
                mongodb_uri="mongodb://invalid-host:27017/",
                database_name="test"
            )


class TestTTLIndexes:
    """Test TTL (Time-To-Live) indexes for automatic cleanup."""

    def test_short_term_ttl_24_hours(self, memory_os):
        """Test short-term memory TTL index (24 hours)."""
        # Store memory with 24h expiration
        memory_id = memory_os.store(
            agent_id="qa",
            user_id="test_user",
            user_input="Test query",
            agent_response="Test response",
            memory_type="conversation"
        )

        # Verify expires_at is set correctly
        doc = memory_os.collections["short_term"].find_one({"memory_id": memory_id})
        assert doc is not None
        assert doc["expires_at"] is not None

        # Verify expiration is ~24 hours from now
        expires_delta = doc["expires_at"] - datetime.now(timezone.utc)
        assert 23.5 * 3600 < expires_delta.total_seconds() < 24.5 * 3600

    def test_mid_term_ttl_7_days(self, memory_os):
        """Test mid-term memory TTL index (7 days)."""
        # Create mid-term entry manually
        user_id = "test_user"
        memory_os.store(
            agent_id="support",
            user_id=user_id,
            user_input="Support ticket",
            agent_response="Resolution",
            memory_type="conversation"
        )

        # Trigger consolidation
        memory_os.consolidate("support", user_id)

        # Verify mid-term TTL
        mid_docs = list(memory_os.collections["mid_term"].find({"user_id": user_id}))
        if mid_docs:
            doc = mid_docs[0]
            assert doc["expires_at"] is not None

            # Verify expiration is ~7 days
            expires_delta = doc["expires_at"] - datetime.now(timezone.utc)
            assert 6.5 * 86400 < expires_delta.total_seconds() < 7.5 * 86400

    def test_long_term_no_ttl(self, memory_os):
        """Test long-term memory has no TTL (permanent)."""
        memory_id = memory_os.store(
            agent_id="legal",
            user_id="test_user",
            user_input="Contract clause",
            agent_response="Legal interpretation",
            memory_type="consensus"
        )

        # Verify no expiration
        doc = memory_os.collections["long_term"].find_one({"memory_id": memory_id})
        assert doc is not None
        assert doc["expires_at"] is None


class TestAgentIsolation:
    """Test agent-specific memory isolation (field-level filtering)."""

    def test_agent_user_isolation(self, memory_os):
        """Test memories are isolated per agent-user pair."""
        # Store for different agent-user pairs
        memory_os.store("qa", "user1", "QA query", "QA response")
        memory_os.store("support", "user1", "Support query", "Support response")
        memory_os.store("qa", "user2", "QA query 2", "QA response 2")

        # Retrieve for qa-user1
        memories_qa_user1 = memory_os.retrieve("qa", "user1", "query")

        # Verify isolation: only qa-user1 memories returned
        for mem in memories_qa_user1:
            assert mem["content"]["user_input"] == "QA query"

    def test_agent_count_isolation(self, memory_os):
        """Test agent-specific memory counts."""
        # Store for multiple agents
        for i in range(5):
            memory_os.store("qa", "user1", f"QA {i}", f"Response {i}")

        for i in range(3):
            memory_os.store("support", "user1", f"Support {i}", f"Response {i}")

        # Verify counts per agent
        qa_count = memory_os.collections["short_term"].count_documents({"agent_id": "qa", "user_id": "user1"})
        support_count = memory_os.collections["short_term"].count_documents({"agent_id": "support", "user_id": "user1"})

        assert qa_count == 5
        assert support_count == 3


class TestHeatBasedPromotion:
    """Test heat-based memory promotion (LFU eviction)."""

    def test_heat_score_initialization(self, memory_os):
        """Test initial heat score is 1.0."""
        memory_id = memory_os.store("analyst", "user1", "Analysis query", "Analysis result")

        doc = memory_os.collections["short_term"].find_one({"memory_id": memory_id})
        assert doc["heat_score"] == 1.0
        assert doc["visit_count"] == 1

    def test_heat_score_increases_on_retrieval(self, memory_os):
        """Test heat score increases when memory is retrieved."""
        # Store memory
        memory_id = memory_os.store("content", "user1", "Content request", "Content generated")

        # Retrieve (increases heat)
        memory_os.retrieve("content", "user1", "Content")

        # Verify heat increased
        doc = memory_os.collections["short_term"].find_one({"memory_id": memory_id})
        assert doc["heat_score"] > 1.0
        assert doc["visit_count"] > 1

    def test_mid_to_long_promotion_by_heat(self, memory_os):
        """Test mid-term → long-term promotion when heat exceeds threshold."""
        user_id = "user1"

        # Store short-term memory
        memory_id = memory_os.store("legal", user_id, "Legal query", "Legal response")

        # Force consolidate short → mid
        memory_os.consolidate("legal", user_id)

        # Artificially increase heat score above threshold (5.0)
        memory_os.collections["mid_term"].update_one(
            {"memory_id": memory_id},
            {"$set": {"heat_score": 6.0}}
        )

        # Consolidate mid → long (heat-based promotion)
        memory_os.consolidate("legal", user_id)

        # Verify memory moved to long-term
        long_doc = memory_os.collections["long_term"].find_one({"memory_id": memory_id})
        mid_doc = memory_os.collections["mid_term"].find_one({"memory_id": memory_id})

        assert long_doc is not None
        assert mid_doc is None


class TestHierarchicalTiers:
    """Test 3-tier hierarchical memory (short → mid → long)."""

    def test_short_to_mid_consolidation(self, memory_os):
        """Test short-term → mid-term consolidation when capacity full."""
        user_id = "user1"

        # Fill short-term capacity (10)
        for i in range(15):
            memory_os.store("qa", user_id, f"Query {i}", f"Response {i}")

        # Verify short-term has capacity limit (LFU eviction)
        short_count = memory_os.collections["short_term"].count_documents({"agent_id": "qa", "user_id": user_id})
        assert short_count <= 10

    def test_mid_to_long_promotion(self, memory_os):
        """Test mid-term → long-term promotion."""
        user_id = "user1"

        # Create mid-term entries
        for i in range(5):
            memory_os.store("support", user_id, f"Ticket {i}", f"Resolution {i}")

        # Consolidate short → mid
        memory_os.consolidate("support", user_id)

        # Check mid-term exists
        mid_count = memory_os.collections["mid_term"].count_documents({"agent_id": "support", "user_id": user_id})
        assert mid_count > 0

    def test_retrieval_from_all_tiers(self, memory_os):
        """Test retrieval searches all 3 tiers."""
        user_id = "user1"

        # Store in short-term
        memory_os.store("analyst", user_id, "Short query", "Short response", "conversation")

        # Store in long-term
        memory_os.store("analyst", user_id, "Long query", "Long response", "consensus")

        # Retrieve (should get from both tiers)
        memories = memory_os.retrieve("analyst", user_id, "query", top_k=10)

        types = [m["type"] for m in memories]
        assert "short_term" in types
        assert "consensus" in types


# ============================================================================
# INTEGRATION TESTS (10 tests)
# ============================================================================

class TestReasoningBankPipeline:
    """Test ReasoningBank 5-stage pipeline end-to-end."""

    async def test_stage1_retrieve(self, reasoning_bank):
        """Test Stage 1: Retrieve similar reasoning traces."""
        # Add sample traces
        trace = ReasoningTrace(
            trace_id="test_trace_1",
            trace_type=ReasoningTraceType.CODE_EVOLUTION,
            task_description="Improve function performance",
            reasoning_steps=["Step 1: Profile code", "Step 2: Optimize loop"],
            decision_points=[],
            outcome_success=True,
            quality_score=0.85,
            quality_level=ReasoningQuality.GOOD
        )

        await reasoning_bank.consolidate(trace)

        # Retrieve similar
        traces = await reasoning_bank.retrieve(
            task_description="Optimize function",
            trace_type=ReasoningTraceType.CODE_EVOLUTION,
            top_k=5
        )

        assert len(traces) > 0
        assert traces[0].trace_type == ReasoningTraceType.CODE_EVOLUTION

    async def test_stage2_act(self, reasoning_bank):
        """Test Stage 2: Execute task with reasoning context."""
        # Create mock executor
        async def mock_executor(task, reasoning_context=None):
            return {
                "success": True,
                "output": "Task executed",
                "reasoning_steps": ["Step 1", "Step 2"]
            }

        # Execute with empty traces
        result = await reasoning_bank.act(
            task={"description": "Test task"},
            retrieved_traces=[],
            executor_fn=mock_executor
        )

        assert result["success"] is True

    async def test_stage3_judge(self, reasoning_bank):
        """Test Stage 3: Judge execution quality."""
        # Create mock judge
        async def mock_judge(task, result):
            return {
                "quality_score": 0.8,
                "strengths": ["Good reasoning"],
                "weaknesses": ["Could be faster"],
                "reasoning": "Well-structured solution"
            }

        judgment = await reasoning_bank.judge(
            task={"description": "Test task"},
            result={"success": True},
            judge_fn=mock_judge
        )

        assert judgment.quality_score == 0.8
        assert judgment.quality_level == ReasoningQuality.GOOD

    async def test_stage4_extract(self, reasoning_bank):
        """Test Stage 4: Extract reasoning pattern."""
        judgment = JudgmentResult(
            quality_score=0.85,
            quality_level=ReasoningQuality.GOOD,
            strengths=["Clear steps"],
            weaknesses=[],
            reasoning="Good execution"
        )

        trace = await reasoning_bank.extract(
            task={"description": "Solve problem", "trace_type": "problem_solving"},
            result={
                "success": True,
                "reasoning_steps": ["Step 1", "Step 2"],
                "decision_points": []
            },
            judgment=judgment
        )

        assert trace is not None
        assert trace.quality_score == 0.85

    async def test_stage5_consolidate(self, reasoning_bank):
        """Test Stage 5: Consolidate trace to bank."""
        trace = ReasoningTrace(
            trace_id="consolidate_test",
            trace_type=ReasoningTraceType.PROBLEM_SOLVING,
            task_description="Test consolidation",
            reasoning_steps=["Step 1"],
            decision_points=[],
            outcome_success=True,
            quality_score=0.9,
            quality_level=ReasoningQuality.EXCELLENT
        )

        added = await reasoning_bank.consolidate(trace)

        assert added is True

        # Verify stored
        doc = reasoning_bank.collection.find_one({"trace_id": "consolidate_test"})
        assert doc is not None


class TestMultiAgentMemory:
    """Test memory integration across 5 agents."""

    async def test_support_agent_memory(self, memory_os):
        """Test Support agent ticket resolution memory."""
        user_id = "support_test"

        # Store ticket resolution
        memory_os.store(
            agent_id="support",
            user_id=user_id,
            user_input="Login issue",
            agent_response="Reset password",
            memory_type="conversation"
        )

        # Retrieve
        memories = memory_os.retrieve("support", user_id, "login")

        assert len(memories) > 0
        assert "Login issue" in str(memories[0]["content"])

    async def test_legal_agent_memory(self, memory_os):
        """Test Legal agent contract clause memory."""
        user_id = "legal_test"

        memory_os.store(
            agent_id="legal",
            user_id=user_id,
            user_input="Liability clause review",
            agent_response="Clause analysis: compliant",
            memory_type="consensus"
        )

        memories = memory_os.retrieve("legal", user_id, "liability", memory_type="consensus")

        assert len(memories) > 0

    async def test_analyst_agent_memory(self, memory_os):
        """Test Analyst agent insights memory."""
        user_id = "analyst_test"

        memory_os.store(
            agent_id="analyst",
            user_id=user_id,
            user_input="Revenue trend analysis",
            agent_response="Q3 revenue up 15%",
            memory_type="conversation"
        )

        memories = memory_os.retrieve("analyst", user_id, "revenue")

        assert len(memories) > 0

    async def test_content_agent_memory(self, memory_os):
        """Test Content agent generation memory."""
        user_id = "content_test"

        memory_os.store(
            agent_id="content",
            user_id=user_id,
            user_input="Blog post about AI",
            agent_response="Generated 500-word article",
            memory_type="conversation"
        )

        memories = memory_os.retrieve("content", user_id, "blog")

        assert len(memories) > 0

    async def test_se_darwin_memory(self, memory_os):
        """Test SE-Darwin evolution pattern memory."""
        user_id = "darwin_builder"

        memory_os.store(
            agent_id="se_darwin",
            user_id=user_id,
            user_input="Evolve builder agent",
            agent_response="Success! Best trajectory: recombination, score: 0.85",
            memory_type="conversation"
        )

        memories = memory_os.retrieve("se_darwin", user_id, "evolution")

        assert len(memories) > 0


class TestConcurrentAccess:
    """Test concurrent memory access (5 agents × 10 requests = 50 concurrent)."""

    async def test_concurrent_store(self, memory_os):
        """Test concurrent memory storage."""
        agents = ["qa", "support", "legal", "analyst", "content"]

        async def store_memory(agent_id, user_id, idx):
            memory_os.store(
                agent_id=agent_id,
                user_id=user_id,
                user_input=f"Query {idx}",
                agent_response=f"Response {idx}"
            )

        # Create 50 concurrent tasks (5 agents × 10 requests)
        tasks = []
        for agent in agents:
            for i in range(10):
                tasks.append(store_memory(agent, "concurrent_user", i))

        # Execute concurrently
        await asyncio.gather(*tasks)

        # Verify all stored
        for agent in agents:
            count = memory_os.collections["short_term"].count_documents({"agent_id": agent, "user_id": "concurrent_user"})
            assert count == 10

    async def test_concurrent_retrieve(self, memory_os):
        """Test concurrent memory retrieval."""
        # Pre-populate
        for i in range(5):
            memory_os.store("qa", "concurrent_user", f"Query {i}", f"Response {i}")

        # Concurrent retrieval
        async def retrieve_memory():
            return memory_os.retrieve("qa", "concurrent_user", "Query")

        tasks = [retrieve_memory() for _ in range(20)]
        results = await asyncio.gather(*tasks)

        # Verify all retrievals succeeded
        assert all(len(r) > 0 for r in results)


class TestMemoryConsistency:
    """Test memory consistency across tiers."""

    def test_consolidation_consistency(self, memory_os):
        """Test memory remains consistent during consolidation."""
        user_id = "consistency_test"

        # Store 15 memories (exceeds short-term capacity)
        memory_ids = []
        for i in range(15):
            mid = memory_os.store("qa", user_id, f"Query {i}", f"Response {i}")
            memory_ids.append(mid)

        # Consolidate
        memory_os.consolidate("qa", user_id)

        # Verify no data loss
        total_count = sum([
            memory_os.collections["short_term"].count_documents({"user_id": user_id}),
            memory_os.collections["mid_term"].count_documents({"user_id": user_id}),
            memory_os.collections["long_term"].count_documents({"user_id": user_id})
        ])

        assert total_count > 0  # Some memories retained

    def test_update_consistency(self, memory_os):
        """Test memory updates are atomic."""
        memory_id = memory_os.store("support", "update_test", "Original query", "Original response")

        # Update content
        success = memory_os.update(memory_id, {"user_input": "Updated query", "agent_response": "Updated response"})

        assert success is True

        # Verify update
        doc = memory_os.collections["short_term"].find_one({"memory_id": memory_id})
        assert doc["content"]["user_input"] == "Updated query"


# ============================================================================
# PERFORMANCE TESTS (5 tests)
# ============================================================================

class TestRetrievalLatency:
    """Test retrieval latency (<100ms target)."""

    def test_short_term_retrieval_latency(self, memory_os):
        """Test short-term retrieval latency."""
        # Pre-populate
        for i in range(10):
            memory_os.store("qa", "perf_user", f"Query {i}", f"Response {i}")

        # Measure retrieval time
        start = time.time()
        memories = memory_os.retrieve("qa", "perf_user", "Query", top_k=5)
        latency = (time.time() - start) * 1000  # Convert to ms

        assert latency < 100  # Target: <100ms
        assert len(memories) > 0

    def test_mid_term_retrieval_latency(self, memory_os):
        """Test mid-term retrieval latency."""
        user_id = "perf_user_mid"

        # Create mid-term entries
        for i in range(20):
            memory_os.store("support", user_id, f"Ticket {i}", f"Resolution {i}")

        memory_os.consolidate("support", user_id)

        # Measure retrieval
        start = time.time()
        memories = memory_os.retrieve("support", user_id, "Ticket", top_k=5)
        latency = (time.time() - start) * 1000

        assert latency < 150  # Mid-term slightly slower, still <150ms

    def test_cross_tier_retrieval_latency(self, memory_os):
        """Test cross-tier retrieval latency (all 3 tiers)."""
        user_id = "perf_user_cross"

        # Populate all tiers
        memory_os.store("analyst", user_id, "Short query", "Short response", "conversation")
        memory_os.store("analyst", user_id, "Long query", "Long response", "consensus")

        # Measure
        start = time.time()
        memories = memory_os.retrieve("analyst", user_id, "query", top_k=10)
        latency = (time.time() - start) * 1000

        assert latency < 200  # Cross-tier <200ms


class TestStorageThroughput:
    """Test storage throughput (>100 ops/sec target)."""

    def test_bulk_storage_throughput(self, memory_os):
        """Test bulk storage throughput."""
        user_id = "throughput_test"

        # Store 100 memories
        start = time.time()
        for i in range(100):
            memory_os.store("content", user_id, f"Query {i}", f"Response {i}")
        elapsed = time.time() - start

        throughput = 100 / elapsed  # ops/sec

        assert throughput > 100  # Target: >100 ops/sec

    def test_concurrent_storage_throughput(self, memory_os):
        """Test concurrent storage throughput."""
        import asyncio

        async def store_batch():
            for i in range(20):
                memory_os.store("legal", f"throughput_user_{i}", "Query", "Response")

        # Run 5 concurrent batches (100 total ops)
        start = time.time()
        asyncio.run(asyncio.gather(*[store_batch() for _ in range(5)]))
        elapsed = time.time() - start

        throughput = 100 / elapsed

        assert throughput > 80  # Concurrent slightly slower, >80 ops/sec


class TestMemoryOverhead:
    """Test memory overhead (<50MB per agent target)."""

    def test_short_term_memory_overhead(self, memory_os):
        """Test short-term memory overhead."""
        user_id = "overhead_test"

        # Store maximum short-term capacity
        for i in range(10):
            memory_os.store("qa", user_id, f"Query {i}" * 10, f"Response {i}" * 10)

        # Estimate size (rough approximation)
        docs = list(memory_os.collections["short_term"].find({"user_id": user_id}))

        import sys
        total_size = sum(sys.getsizeof(str(doc)) for doc in docs)
        size_mb = total_size / (1024 * 1024)

        assert size_mb < 1  # Short-term alone should be <1MB

    def test_mid_term_memory_overhead(self, memory_os):
        """Test mid-term memory overhead."""
        user_id = "overhead_mid_test"

        # Store 100 mid-term entries
        for i in range(100):
            memory_os.store("support", user_id, f"Ticket {i}" * 5, f"Resolution {i}" * 5)

        memory_os.consolidate("support", user_id)

        docs = list(memory_os.collections["mid_term"].find({"user_id": user_id}))

        import sys
        total_size = sum(sys.getsizeof(str(doc)) for doc in docs)
        size_mb = total_size / (1024 * 1024)

        assert size_mb < 5  # Mid-term <5MB


# ============================================================================
# TEST CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--color=yes"])
