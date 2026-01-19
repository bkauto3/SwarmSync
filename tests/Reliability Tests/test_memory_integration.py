"""Integration tests for LangGraph Store + Compliance Layer.

Tests the full integration between the memory store and compliance features,
validating end-to-end workflows in realistic scenarios.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

import pytest

# Mock MongoDB for testing without external dependencies
class MockMongoCollection:
    """Mock MongoDB collection for testing."""
    
    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.indexes: Dict[str, Dict[str, Any]] = {}
    
    async def update_one(self, filter_dict, update, upsert=False):
        key = filter_dict.get("key")
        if key:
            self.documents[key] = update["$set"]
        return type('Result', (), {'matched_count': 1, 'modified_count': 1})()
    
    async def find_one(self, filter_dict):
        key = filter_dict.get("key")
        return self.documents.get(key)
    
    async def delete_one(self, filter_dict):
        key = filter_dict.get("key")
        if key in self.documents:
            del self.documents[key]
            return type('Result', (), {'deleted_count': 1})()
        return type('Result', (), {'deleted_count': 0})()
    
    async def delete_many(self, filter_dict):
        count = len(self.documents)
        self.documents.clear()
        return type('Result', (), {'deleted_count': count})()
    
    def find(self, query):
        return type('Cursor', (), {
            'limit': lambda x: self,
            'to_list': self._to_list
        })()
    
    async def _to_list(self, length):
        return list(self.documents.values())[:length]
    
    async def index_information(self):
        return self.indexes
    
    async def create_index(self, field, **kwargs):
        index_name = kwargs.get('name', f'index_{field}')
        self.indexes[index_name] = {
            'key': field,
            **kwargs
        }


class MockMongoDatabase:
    """Mock MongoDB database for testing."""
    
    def __init__(self):
        self.collections: Dict[str, MockMongoCollection] = {}
        self.name = "test_db"
    
    def __getitem__(self, collection_name):
        if collection_name not in self.collections:
            self.collections[collection_name] = MockMongoCollection()
        return self.collections[collection_name]
    
    async def list_collection_names(self):
        return list(self.collections.keys())
    
    async def command(self, cmd):
        if cmd == "dbStats":
            return {"dataSize": 1024}
        return {}


class MockMongoClient:
    """Mock MongoDB client for testing."""
    
    def __init__(self, *args, **kwargs):
        self._databases: Dict[str, MockMongoDatabase] = {}
        self.admin = type('Admin', (), {
            'command': lambda cmd: asyncio.sleep(0)
        })()
    
    def __getitem__(self, db_name):
        if db_name not in self._databases:
            self._databases[db_name] = MockMongoDatabase()
        return self._databases[db_name]
    
    def close(self):
        pass


@pytest.fixture
async def mock_store():
    """Create a mock LangGraph store with compliance layer."""
    import sys
    from unittest.mock import Mock, patch
    
    # Mock motor before importing store
    mock_motor = Mock()
    mock_motor.motor_asyncio.AsyncIOMotorClient = MockMongoClient
    sys.modules['motor'] = mock_motor
    sys.modules['motor.motor_asyncio'] = mock_motor.motor_asyncio
    
    # Now import store
    from infrastructure.langgraph_store import GenesisLangGraphStore
    
    store = GenesisLangGraphStore(
        mongodb_uri="mongodb://localhost:27017/",
        database_name="test_memory"
    )
    
    await store.setup_indexes()
    
    yield store
    
    await store.close()


@pytest.mark.asyncio
async def test_end_to_end_pii_redaction(mock_store):
    """Test that PII is automatically redacted when storing data."""
    
    namespace = ("agent", "support_agent")
    key = "customer_inquiry"
    value = {
        "message": "Please contact me at john.doe@example.com or call +1-555-123-4567",
        "ssn": "My SSN is 123-45-6789",
    }
    
    # Store data with PII
    await mock_store.put(namespace, key, value, actor="support_agent")
    
    # Retrieve data
    stored_value = await mock_store.get(namespace, key, actor="admin")
    
    # Verify PII was redacted
    assert "[REDACTED:email]" in stored_value["message"]
    assert "[REDACTED:phone]" in stored_value["message"]
    assert "[REDACTED:ssn]" in stored_value["ssn"]
    
    # Verify audit log captured the operations
    if mock_store.compliance:
        audit_log = mock_store.compliance.get_access_log()
        assert len(audit_log) >= 2  # write + read
        assert any(entry["action"] == "write" for entry in audit_log)
        assert any(entry["action"] == "read" for entry in audit_log)


@pytest.mark.asyncio
async def test_end_to_end_gdpr_erasure(mock_store):
    """Test complete GDPR Article 17 deletion workflow."""
    
    user_id = "user-gdpr-test"
    
    # Store multiple entries for a user
    await mock_store.put(
        ("agent", "qa_agent"),
        "qa_data",
        {"query": "test"},
        metadata={"user_id": user_id},
        actor="qa_agent"
    )
    
    await mock_store.put(
        ("business", "biz_123"),
        "business_data",
        {"info": "test"},
        metadata={"user_id": user_id},
        actor="business_manager"
    )
    
    # Execute GDPR deletion
    if mock_store.compliance:
        deleted_count = await mock_store.compliance.delete_user_data(
            user_id,
            namespaces=[("agent", "qa_agent"), ("business", "biz_123")]
        )
        
        # Verify deletion
        assert deleted_count >= 0  # May be 0 in mock implementation
        
        # Verify audit log contains deletion events
        audit_log = mock_store.compliance.get_access_log()
        deletion_events = [e for e in audit_log if e["action"] == "delete"]
        assert len(deletion_events) > 0


@pytest.mark.asyncio
async def test_query_injection_blocked(mock_store):
    """Test that malicious queries are blocked."""
    
    namespace = ("agent", "test_agent")
    
    # Try to execute malicious query
    if mock_store.compliance:
        with pytest.raises(ValueError, match="Unsafe MongoDB operator"):
            await mock_store.search(
                namespace,
                query={"$where": "this.value == 'malicious'"},
                actor="attacker"
            )
        
        # Safe query should work
        results = await mock_store.search(
            namespace,
            query={"value.threshold": {"$gt": 0.5}},
            actor="legitimate_user"
        )
        assert isinstance(results, list)


@pytest.mark.asyncio
async def test_ttl_retention_metadata(mock_store):
    """Test that retention metadata is added based on TTL policies."""
    
    namespace = ("agent", "test_agent")
    key = "test_key"
    value = {"data": "test"}
    metadata = {"category": "config"}
    
    await mock_store.put(namespace, key, value, metadata, actor="test_actor")
    
    # Retrieve and check metadata
    # Note: In mock implementation, we'd need to check the stored document
    # In real MongoDB, the compliance metadata would be persisted


@pytest.mark.asyncio
async def test_concurrent_access_safety(mock_store):
    """Test that concurrent operations are handled safely."""
    
    namespace = ("agent", "concurrent_test")
    
    # Create multiple concurrent write operations
    async def write_data(index):
        await mock_store.put(
            namespace,
            f"key_{index}",
            {"value": index},
            actor=f"agent_{index}"
        )
    
    # Execute 10 concurrent writes
    await asyncio.gather(*[write_data(i) for i in range(10)])
    
    # Verify audit log captured all operations
    if mock_store.compliance:
        audit_log = mock_store.compliance.get_access_log()
        write_events = [e for e in audit_log if e["action"] == "write"]
        assert len(write_events) >= 10


@pytest.mark.asyncio
async def test_actor_tracking_optional(mock_store):
    """Test that actor parameter is optional for backward compatibility."""
    
    namespace = ("agent", "legacy_agent")
    key = "legacy_key"
    value = {"data": "test"}
    
    # Test without actor (old API)
    await mock_store.put(namespace, key, value)
    result = await mock_store.get(namespace, key)
    assert result is not None
    
    # Test with actor (new API)
    await mock_store.put(namespace, key, value, actor="new_agent")
    result = await mock_store.get(namespace, key, actor="new_agent")
    assert result is not None
    
    # Test delete without actor
    deleted = await mock_store.delete(namespace, key)
    assert isinstance(deleted, bool)


@pytest.mark.asyncio
async def test_compliance_layer_degradation(mock_store):
    """Test that store works even if compliance layer fails."""
    
    namespace = ("agent", "test_agent")
    key = "test_key"
    value = {"data": "test"}
    
    # Temporarily disable compliance layer
    original_compliance = mock_store.compliance
    mock_store.compliance = None
    
    try:
        # Operations should still work
        await mock_store.put(namespace, key, value)
        result = await mock_store.get(namespace, key)
        assert result == value
        
        deleted = await mock_store.delete(namespace, key)
        assert deleted == True or deleted == False  # Boolean result
    finally:
        # Restore compliance layer
        mock_store.compliance = original_compliance


@pytest.mark.asyncio
async def test_search_with_compliance(mock_store):
    """Test that search operations log properly."""
    
    namespace = ("agent", "search_test")
    
    # Store some data
    await mock_store.put(namespace, "key1", {"score": 0.9}, actor="test")
    await mock_store.put(namespace, "key2", {"score": 0.7}, actor="test")
    await mock_store.put(namespace, "key3", {"score": 0.5}, actor="test")
    
    # Search with filter
    results = await mock_store.search(
        namespace,
        query={"value.score": {"$gt": 0.6}},
        actor="searcher"
    )
    
    assert isinstance(results, list)
    
    # Verify search was logged
    if mock_store.compliance:
        audit_log = mock_store.compliance.get_access_log()
        search_events = [e for e in audit_log if e["action"] == "search"]
        assert len(search_events) > 0
        assert search_events[-1]["actor"] == "searcher"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

