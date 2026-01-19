"""
Unit Tests for GenesisMemoryStore

Tests cover:
1. Save/retrieve operations with different namespaces
2. Search within namespaces
3. Metadata tracking (access counts, timestamps)
4. Error handling (invalid namespaces, missing keys)
5. Cross-agent sharing scenarios
6. Namespace isolation
7. Performance (async operations)

Target: 20+ tests, 100% coverage of core functionality
"""

import asyncio
import json
import time
from datetime import datetime

import pytest

from infrastructure.memory_store import (
    GenesisMemoryStore,
    InMemoryBackend,
    MemoryEntry,
    MemoryMetadata,
)


class TestMemoryMetadata:
    """Test MemoryMetadata dataclass"""

    def test_metadata_creation(self):
        """Test metadata is created with defaults"""
        metadata = MemoryMetadata()

        assert metadata.access_count == 0
        assert metadata.compressed is False
        assert metadata.compression_ratio is None
        assert metadata.tags == []
        assert metadata.created_at is not None
        assert metadata.last_accessed is not None

    def test_metadata_to_dict(self):
        """Test metadata serialization"""
        metadata = MemoryMetadata(
            access_count=5,
            compressed=True,
            compression_ratio=0.71,
            tags=["important", "verified"]
        )

        data = metadata.to_dict()

        assert data["access_count"] == 5
        assert data["compressed"] is True
        assert data["compression_ratio"] == 0.71
        assert "important" in data["tags"]

    def test_metadata_from_dict(self):
        """Test metadata deserialization"""
        data = {
            "created_at": "2025-10-22T00:00:00Z",
            "last_accessed": "2025-10-22T01:00:00Z",
            "access_count": 10,
            "compressed": False,
            "compression_ratio": None,
            "tags": ["test"]
        }

        metadata = MemoryMetadata.from_dict(data)

        assert metadata.access_count == 10
        assert metadata.tags == ["test"]


class TestMemoryEntry:
    """Test MemoryEntry dataclass"""

    def test_entry_creation(self):
        """Test memory entry creation"""
        entry = MemoryEntry(
            namespace=("agent", "qa_001"),
            key="test_procedure",
            value={"steps": [1, 2, 3]}
        )

        assert entry.namespace == ("agent", "qa_001")
        assert entry.key == "test_procedure"
        assert entry.value == {"steps": [1, 2, 3]}
        assert entry.entry_id is not None

    def test_entry_to_dict(self):
        """Test entry serialization"""
        entry = MemoryEntry(
            namespace=("business", "saas_001"),
            key="deploy_config",
            value={"port": 8000}
        )

        data = entry.to_dict()

        assert data["namespace"] == ("business", "saas_001")
        assert data["key"] == "deploy_config"
        assert data["value"]["port"] == 8000
        assert "metadata" in data

    def test_entry_from_dict(self):
        """Test entry deserialization"""
        data = {
            "entry_id": "test-123",
            "namespace": ["system", "global"],
            "key": "config",
            "value": {"setting": "value"},
            "metadata": {
                "access_count": 5,
                "compressed": False,
                "tags": []
            }
        }

        entry = MemoryEntry.from_dict(data)

        assert entry.entry_id == "test-123"
        assert entry.namespace == ("system", "global")
        assert entry.key == "config"
        assert entry.metadata.access_count == 5


class TestInMemoryBackend:
    """Test InMemoryBackend storage"""

    @pytest.mark.asyncio
    async def test_put_and_get(self):
        """Test basic put/get operations"""
        backend = InMemoryBackend()

        # Store entry
        entry = await backend.put(
            namespace=("agent", "qa_001"),
            key="test_data",
            value={"result": "success"}
        )

        assert entry is not None
        assert entry.value == {"result": "success"}

        # Retrieve entry
        retrieved = await backend.get(
            namespace=("agent", "qa_001"),
            key="test_data"
        )

        assert retrieved is not None
        assert retrieved.value == {"result": "success"}
        assert retrieved.metadata.access_count == 1  # Incremented on get

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        """Test get returns None for missing key"""
        backend = InMemoryBackend()

        result = await backend.get(
            namespace=("agent", "qa_001"),
            key="missing_key"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_access_tracking(self):
        """Test access count increments"""
        backend = InMemoryBackend()

        await backend.put(
            namespace=("agent", "qa_001"),
            key="popular_data",
            value={"data": "test"}
        )

        # Access multiple times
        for i in range(5):
            entry = await backend.get(
                namespace=("agent", "qa_001"),
                key="popular_data"
            )
            assert entry.metadata.access_count == i + 1

    @pytest.mark.asyncio
    async def test_namespace_isolation(self):
        """Test different namespaces are isolated"""
        backend = InMemoryBackend()

        # Store in agent namespace
        await backend.put(
            namespace=("agent", "qa_001"),
            key="shared_key",
            value={"source": "qa_agent"}
        )

        # Store in business namespace with same key
        await backend.put(
            namespace=("business", "saas_001"),
            key="shared_key",
            value={"source": "business"}
        )

        # Retrieve from each namespace
        qa_entry = await backend.get(("agent", "qa_001"), "shared_key")
        business_entry = await backend.get(("business", "saas_001"), "shared_key")

        assert qa_entry.value["source"] == "qa_agent"
        assert business_entry.value["source"] == "business"

    @pytest.mark.asyncio
    async def test_search(self):
        """Test search functionality"""
        backend = InMemoryBackend()

        # Store multiple entries
        await backend.put(
            namespace=("agent", "qa_001"),
            key="test_procedure_1",
            value={"type": "unit_test", "coverage": 90}
        )
        await backend.put(
            namespace=("agent", "qa_001"),
            key="test_procedure_2",
            value={"type": "integration_test", "coverage": 85}
        )
        await backend.put(
            namespace=("agent", "qa_001"),
            key="deploy_config",
            value={"port": 8000}
        )

        # Search for "test"
        results = await backend.search(
            namespace=("agent", "qa_001"),
            query="test",
            limit=10
        )

        assert len(results) == 2
        assert all("test" in entry.key.lower() or "test" in json.dumps(entry.value).lower() for entry in results)

    @pytest.mark.asyncio
    async def test_search_limit(self):
        """Test search respects limit"""
        backend = InMemoryBackend()

        # Store 10 entries
        for i in range(10):
            await backend.put(
                namespace=("agent", "qa_001"),
                key=f"test_{i}",
                value={"index": i}
            )

        # Search with limit=5
        results = await backend.search(
            namespace=("agent", "qa_001"),
            query="test",
            limit=5
        )

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test delete operation"""
        backend = InMemoryBackend()

        # Store entry
        await backend.put(
            namespace=("agent", "qa_001"),
            key="temp_data",
            value={"temporary": True}
        )

        # Delete entry
        deleted = await backend.delete(
            namespace=("agent", "qa_001"),
            key="temp_data"
        )

        assert deleted is True

        # Verify deleted
        entry = await backend.get(
            namespace=("agent", "qa_001"),
            key="temp_data"
        )
        assert entry is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        """Test delete returns False for missing key"""
        backend = InMemoryBackend()

        deleted = await backend.delete(
            namespace=("agent", "qa_001"),
            key="missing_key"
        )

        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_keys(self):
        """Test list_keys returns all keys in namespace"""
        backend = InMemoryBackend()

        # Store multiple entries
        await backend.put(("agent", "qa_001"), "key1", {"a": 1})
        await backend.put(("agent", "qa_001"), "key2", {"b": 2})
        await backend.put(("agent", "qa_001"), "key3", {"c": 3})

        # List keys
        keys = await backend.list_keys(("agent", "qa_001"))

        assert len(keys) == 3
        assert set(keys) == {"key1", "key2", "key3"}

    @pytest.mark.asyncio
    async def test_clear_namespace(self):
        """Test clear_namespace removes all entries"""
        backend = InMemoryBackend()

        # Store entries
        await backend.put(("agent", "qa_001"), "key1", {"a": 1})
        await backend.put(("agent", "qa_001"), "key2", {"b": 2})

        # Clear namespace
        count = await backend.clear_namespace(("agent", "qa_001"))

        assert count == 2

        # Verify cleared
        keys = await backend.list_keys(("agent", "qa_001"))
        assert len(keys) == 0


class TestGenesisMemoryStore:
    """Test GenesisMemoryStore high-level API"""

    @pytest.mark.asyncio
    async def test_save_and_get_memory(self):
        """Test save and retrieve memory"""
        memory = GenesisMemoryStore()

        # Save memory
        entry_id = await memory.save_memory(
            namespace=("agent", "qa_001"),
            key="test_procedure",
            value={"steps": [1, 2, 3], "coverage": 95}
        )

        assert entry_id is not None

        # Retrieve memory
        value = await memory.get_memory(
            namespace=("agent", "qa_001"),
            key="test_procedure"
        )

        assert value is not None
        assert value["coverage"] == 95
        assert value["steps"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_get_missing_memory_with_default(self):
        """Test get returns default for missing key"""
        memory = GenesisMemoryStore()

        value = await memory.get_memory(
            namespace=("agent", "qa_001"),
            key="missing",
            default={"fallback": True}
        )

        assert value == {"fallback": True}

    @pytest.mark.asyncio
    async def test_save_with_tags(self):
        """Test save memory with tags"""
        memory = GenesisMemoryStore()

        await memory.save_memory(
            namespace=("agent", "qa_001"),
            key="important_data",
            value={"data": "test"},
            tags=["important", "verified"]
        )

        # Retrieve with metadata
        entry = await memory.get_memory_with_metadata(
            namespace=("agent", "qa_001"),
            key="important_data"
        )

        assert "important" in entry.metadata.tags
        assert "verified" in entry.metadata.tags

    @pytest.mark.asyncio
    async def test_search_memories(self):
        """Test search memories"""
        memory = GenesisMemoryStore()

        # Save multiple memories
        await memory.save_memory(
            namespace=("agent", "qa_001"),
            key="test_unit",
            value={"type": "unit", "coverage": 90}
        )
        await memory.save_memory(
            namespace=("agent", "qa_001"),
            key="test_integration",
            value={"type": "integration", "coverage": 85}
        )

        # Search
        results = await memory.search_memories(
            namespace=("agent", "qa_001"),
            query="coverage",
            limit=10
        )

        assert len(results) == 2
        assert all("coverage" in r for r in results)

    @pytest.mark.asyncio
    async def test_search_with_metadata(self):
        """Test search returns full entries with metadata"""
        memory = GenesisMemoryStore()

        await memory.save_memory(
            namespace=("agent", "qa_001"),
            key="test_data",
            value={"result": "success"}
        )

        # Search with metadata
        entries = await memory.search_memories_with_metadata(
            namespace=("agent", "qa_001"),
            query="success",
            limit=10
        )

        assert len(entries) == 1
        assert entries[0].metadata.access_count >= 0

    @pytest.mark.asyncio
    async def test_delete_memory(self):
        """Test delete memory"""
        memory = GenesisMemoryStore()

        # Save and delete
        await memory.save_memory(
            namespace=("agent", "qa_001"),
            key="temp",
            value={"temporary": True}
        )

        deleted = await memory.delete_memory(
            namespace=("agent", "qa_001"),
            key="temp"
        )

        assert deleted is True

        # Verify deleted
        value = await memory.get_memory(
            namespace=("agent", "qa_001"),
            key="temp"
        )

        assert value is None

    @pytest.mark.asyncio
    async def test_list_keys(self):
        """Test list keys in namespace"""
        memory = GenesisMemoryStore()

        # Save memories
        await memory.save_memory(("agent", "qa_001"), "key1", {"a": 1})
        await memory.save_memory(("agent", "qa_001"), "key2", {"b": 2})

        # List keys
        keys = await memory.list_keys(("agent", "qa_001"))

        assert len(keys) == 2
        assert "key1" in keys
        assert "key2" in keys

    @pytest.mark.asyncio
    async def test_clear_namespace(self):
        """Test clear namespace"""
        memory = GenesisMemoryStore()

        # Save memories
        await memory.save_memory(("agent", "qa_001"), "key1", {"a": 1})
        await memory.save_memory(("agent", "qa_001"), "key2", {"b": 2})

        # Clear
        count = await memory.clear_namespace(("agent", "qa_001"))

        assert count == 2

        # Verify cleared
        keys = await memory.list_keys(("agent", "qa_001"))
        assert len(keys) == 0

    @pytest.mark.asyncio
    async def test_namespace_stats(self):
        """Test get namespace statistics"""
        memory = GenesisMemoryStore()

        # Save memories
        await memory.save_memory(
            ("agent", "qa_001"),
            "key1",
            {"data": "a" * 100}
        )
        await memory.save_memory(
            ("agent", "qa_001"),
            "key2",
            {"data": "b" * 100}
        )

        # Get stats
        stats = await memory.get_namespace_stats(("agent", "qa_001"))

        assert stats["total_entries"] == 2
        assert stats["total_size_bytes"] > 0
        assert stats["avg_size_bytes"] > 0

    @pytest.mark.asyncio
    async def test_cross_agent_sharing(self):
        """Test agents can share memories via business namespace"""
        memory = GenesisMemoryStore()

        # Agent 1 saves to business namespace
        await memory.save_memory(
            namespace=("business", "saas_001"),
            key="deploy_procedure",
            value={
                "steps": ["build", "test", "deploy"],
                "verified_by": ["qa_agent", "deploy_agent"],
                "success_rate": 0.95
            }
        )

        # Agent 2 retrieves from same business namespace
        procedure = await memory.get_memory(
            namespace=("business", "saas_001"),
            key="deploy_procedure"
        )

        assert procedure is not None
        assert procedure["success_rate"] == 0.95
        assert "qa_agent" in procedure["verified_by"]

    @pytest.mark.asyncio
    async def test_invalid_namespace_format(self):
        """Test invalid namespace raises error"""
        memory = GenesisMemoryStore()

        with pytest.raises(ValueError, match="Namespace must be.*tuple"):
            await memory.save_memory(
                namespace="invalid",  # Should be tuple
                key="test",
                value={"data": "test"}
            )

    @pytest.mark.asyncio
    async def test_invalid_value_type(self):
        """Test non-dict value raises error"""
        memory = GenesisMemoryStore()

        with pytest.raises(ValueError, match="Value must be dict"):
            await memory.save_memory(
                namespace=("agent", "qa_001"),
                key="test",
                value="string_not_dict"  # Should be dict
            )

    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test concurrent read/write operations"""
        memory = GenesisMemoryStore()

        # Save initial memory
        await memory.save_memory(
            namespace=("agent", "qa_001"),
            key="concurrent_test",
            value={"counter": 0}
        )

        # Concurrent reads
        async def read_memory():
            return await memory.get_memory(
                namespace=("agent", "qa_001"),
                key="concurrent_test"
            )

        # Run 10 concurrent reads
        results = await asyncio.gather(*[read_memory() for _ in range(10)])

        # All reads should succeed
        assert len(results) == 10
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_performance_benchmark(self):
        """Benchmark basic operations (target: <100ms P95)"""
        memory = GenesisMemoryStore()

        # Warm up
        await memory.save_memory(
            namespace=("agent", "qa_001"),
            key="warmup",
            value={"data": "test"}
        )

        # Benchmark saves
        save_times = []
        for i in range(100):
            start = time.perf_counter()
            await memory.save_memory(
                namespace=("agent", "qa_001"),
                key=f"bench_key_{i}",
                value={"index": i, "data": "x" * 100}
            )
            duration = (time.perf_counter() - start) * 1000  # Convert to ms
            save_times.append(duration)

        # Benchmark gets
        get_times = []
        for i in range(100):
            start = time.perf_counter()
            await memory.get_memory(
                namespace=("agent", "qa_001"),
                key=f"bench_key_{i}"
            )
            duration = (time.perf_counter() - start) * 1000
            get_times.append(duration)

        # Calculate P95
        save_p95 = sorted(save_times)[94]  # 95th percentile
        get_p95 = sorted(get_times)[94]

        print(f"\nPerformance Benchmark (InMemoryBackend):")
        print(f"  Save P95: {save_p95:.2f}ms")
        print(f"  Get P95: {get_p95:.2f}ms")

        # Target: <100ms P95
        # InMemory backend should be much faster (typically <1ms)
        assert save_p95 < 100, f"Save P95 {save_p95:.2f}ms exceeds 100ms target"
        assert get_p95 < 100, f"Get P95 {get_p95:.2f}ms exceeds 100ms target"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
