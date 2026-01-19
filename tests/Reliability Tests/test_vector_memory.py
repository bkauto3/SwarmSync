"""
Tests for VectorMemory

Validates vector memory functionality with TEI embeddings:
- Store interactions with embeddings
- Similarity search with filtering
- Batch operations
- MongoDB integration
- Statistics tracking

Author: Alex (E2E Testing Lead)
Date: November 4, 2025
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
import numpy as np

from infrastructure.memory.vector_memory import (
    VectorMemory,
    VectorMemoryStats,
    get_vector_memory,
    reset_vector_memory
)


@pytest.fixture
def vector_memory():
    """Create VectorMemory for testing."""
    vm = VectorMemory(
        mongodb_uri="mongodb://localhost:27017",
        enable_otel=False
    )
    yield vm
    # Cleanup
    if vm._connected:
        asyncio.run(vm.close())


@pytest.fixture
def mock_tei_embedding():
    """Mock TEI embedding response."""
    return np.random.rand(768)


class TestVectorMemoryStats:
    """Test vector memory statistics."""
    
    def test_stats_initialization(self):
        """Test stats initialization."""
        stats = VectorMemoryStats()
        assert stats.total_stores == 0
        assert stats.total_searches == 0
        assert stats.errors == 0
    
    def test_stats_to_dict(self):
        """Test stats to dictionary."""
        stats = VectorMemoryStats(total_stores=10, total_searches=5)
        result = stats.to_dict()
        assert result["total_stores"] == 10
        assert result["total_searches"] == 5


class TestVectorMemory:
    """Test VectorMemory class."""
    
    def test_initialization(self, vector_memory):
        """Test VectorMemory initialization."""
        assert vector_memory.database_name == "genesis_memory"
        assert vector_memory.collection_name == "agent_interactions"
        assert vector_memory.embedding_dim == 768
        assert not vector_memory._connected
    
    @pytest.mark.asyncio
    async def test_store_interaction(self, vector_memory, mock_tei_embedding):
        """Test storing interaction."""
        with patch.object(vector_memory, 'connect') as mock_connect:
            mock_connect.return_value = None
            vector_memory._connected = True
            
            with patch.object(vector_memory.tei, 'embed_single') as mock_embed:
                mock_embed.return_value = mock_tei_embedding
                
                with patch.object(vector_memory, 'collection') as mock_collection:
                    mock_result = Mock()
                    mock_result.inserted_id = "test_id_123"
                    mock_collection.insert_one = AsyncMock(return_value=mock_result)
                    
                    interaction_id = await vector_memory.store_interaction(
                        agent_id="qa_agent",
                        interaction="Fixed Stripe bug",
                        metadata={"business_type": "ecommerce"}
                    )
                    
                    assert interaction_id == "test_id_123"
                    assert vector_memory.stats.total_stores == 1
                    assert vector_memory.stats.total_embeddings_generated == 1
    
    @pytest.mark.asyncio
    async def test_search_similar(self, vector_memory, mock_tei_embedding):
        """Test similarity search."""
        with patch.object(vector_memory, 'connect') as mock_connect:
            mock_connect.return_value = None
            vector_memory._connected = True
            
            with patch.object(vector_memory.tei, 'embed_single') as mock_embed:
                mock_embed.return_value = mock_tei_embedding
                
                with patch.object(vector_memory, 'collection') as mock_collection:
                    mock_cursor = Mock()
                    mock_results = [
                        {
                            "agent_id": "qa_agent",
                            "interaction": "Fixed payment bug",
                            "score": 0.95
                        },
                        {
                            "agent_id": "qa_agent",
                            "interaction": "Stripe integration",
                            "score": 0.87
                        }
                    ]
                    mock_cursor.to_list = AsyncMock(return_value=mock_results)
                    mock_collection.aggregate.return_value = mock_cursor
                    
                    results = await vector_memory.search_similar(
                        query="Payment integration issue",
                        limit=5,
                        agent_id="qa_agent"
                    )
                    
                    assert len(results) == 2
                    assert results[0]["score"] == 0.95
                    assert vector_memory.stats.total_searches == 1
    
    @pytest.mark.asyncio
    async def test_search_similar_with_filters(self, vector_memory, mock_tei_embedding):
        """Test similarity search with metadata filters."""
        with patch.object(vector_memory, 'connect') as mock_connect:
            mock_connect.return_value = None
            vector_memory._connected = True
            
            with patch.object(vector_memory.tei, 'embed_single') as mock_embed:
                mock_embed.return_value = mock_tei_embedding
                
                with patch.object(vector_memory, 'collection') as mock_collection:
                    mock_cursor = Mock()
                    mock_cursor.to_list = AsyncMock(return_value=[])
                    mock_collection.aggregate.return_value = mock_cursor
                    
                    results = await vector_memory.search_similar(
                        query="test",
                        agent_id="builder_agent",
                        business_type="saas",
                        min_score=0.8
                    )
                    
                    # Verify aggregate was called with correct pipeline
                    assert mock_collection.aggregate.called
                    pipeline = mock_collection.aggregate.call_args[0][0]
                    
                    # Check for vectorSearch stage
                    assert any("$vectorSearch" in stage for stage in pipeline)
    
    @pytest.mark.asyncio
    async def test_store_batch(self, vector_memory):
        """Test batch store operations."""
        with patch.object(vector_memory, 'connect') as mock_connect:
            mock_connect.return_value = None
            vector_memory._connected = True
            
            with patch.object(vector_memory.tei, 'embed_batch') as mock_embed:
                mock_embed.return_value = np.random.rand(3, 768)
                
                with patch.object(vector_memory, 'collection') as mock_collection:
                    mock_result = Mock()
                    mock_result.inserted_ids = ["id1", "id2", "id3"]
                    mock_collection.insert_many = AsyncMock(return_value=mock_result)
                    
                    interactions = [
                        {
                            "agent_id": "qa_agent",
                            "interaction": "Fixed bug 1",
                            "metadata": {}
                        },
                        {
                            "agent_id": "builder_agent",
                            "interaction": "Built feature 2",
                            "metadata": {}
                        },
                        {
                            "agent_id": "deploy_agent",
                            "interaction": "Deployed app 3",
                            "metadata": {}
                        }
                    ]
                    
                    ids = await vector_memory.store_batch(interactions)
                    
                    assert len(ids) == 3
                    assert vector_memory.stats.total_stores == 3
                    assert vector_memory.stats.total_embeddings_generated == 3
    
    @pytest.mark.asyncio
    async def test_store_batch_empty(self, vector_memory):
        """Test batch store with empty list."""
        ids = await vector_memory.store_batch([])
        assert ids == []
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, vector_memory):
        """Test get interaction by ID."""
        # Use a valid ObjectId format
        from bson import ObjectId
        test_id = str(ObjectId())

        with patch.object(vector_memory, 'connect') as mock_connect:
            mock_connect.return_value = None
            vector_memory._connected = True

            # Create a mock collection
            mock_collection = Mock()
            mock_doc = {
                "_id": ObjectId(test_id),
                "agent_id": "qa_agent",
                "interaction": "test"
            }
            mock_collection.find_one = AsyncMock(return_value=mock_doc)

            # Set the collection directly
            vector_memory.collection = mock_collection

            result = await vector_memory.get_by_id(test_id)

            assert result is not None
            assert result["agent_id"] == "qa_agent"
    
    @pytest.mark.asyncio
    async def test_delete_by_agent(self, vector_memory):
        """Test delete interactions by agent."""
        with patch.object(vector_memory, 'connect') as mock_connect:
            mock_connect.return_value = None
            vector_memory._connected = True
            
            with patch.object(vector_memory, 'collection') as mock_collection:
                mock_result = Mock()
                mock_result.deleted_count = 5
                mock_collection.delete_many = AsyncMock(return_value=mock_result)
                
                count = await vector_memory.delete_by_agent("qa_agent")
                
                assert count == 5
    
    @pytest.mark.asyncio
    async def test_error_handling(self, vector_memory, mock_tei_embedding):
        """Test error handling in search."""
        with patch.object(vector_memory, 'connect') as mock_connect:
            mock_connect.return_value = None
            vector_memory._connected = True
            
            with patch.object(vector_memory.tei, 'embed_single') as mock_embed:
                mock_embed.return_value = mock_tei_embedding
                
                with patch.object(vector_memory, 'collection') as mock_collection:
                    mock_collection.aggregate.side_effect = Exception("MongoDB error")
                    
                    # Should return empty list on error (graceful degradation)
                    results = await vector_memory.search_similar("test")
                    
                    assert results == []
                    assert vector_memory.stats.errors == 1
    
    def test_get_stats(self, vector_memory):
        """Test get statistics."""
        vector_memory.stats.total_stores = 10
        vector_memory.stats.total_searches = 5
        
        stats = vector_memory.get_stats()
        assert stats.total_stores == 10
        assert stats.total_searches == 5
    
    def test_reset_stats(self, vector_memory):
        """Test reset statistics."""
        vector_memory.stats.total_stores = 10
        vector_memory.reset_stats()
        
        assert vector_memory.stats.total_stores == 0


class TestVectorMemorySingleton:
    """Test VectorMemory singleton pattern."""
    
    def test_get_vector_memory(self):
        """Test get singleton instance."""
        reset_vector_memory()
        
        vm1 = get_vector_memory()
        vm2 = get_vector_memory()
        
        assert vm1 is vm2
    
    def test_reset_vector_memory(self):
        """Test reset singleton."""
        reset_vector_memory()
        
        vm1 = get_vector_memory()
        reset_vector_memory()
        vm2 = get_vector_memory()
        
        assert vm1 is not vm2


@pytest.mark.integration
class TestVectorMemoryIntegration:
    """Integration tests (require MongoDB + TEI)."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test full store and search workflow."""
        vm = VectorMemory(enable_otel=False)
        
        try:
            await vm.connect()
        except Exception:
            pytest.skip("MongoDB not available")
        
        # Store interaction
        interaction_id = await vm.store_interaction(
            agent_id="test_agent",
            interaction="Test interaction for integration test",
            metadata={"test": True}
        )
        
        assert interaction_id is not None
        
        # Search similar
        results = await vm.search_similar(
            query="Test interaction",
            limit=5
        )
        
        # Should find the interaction we just stored
        assert len(results) > 0
        
        # Cleanup
        await vm.delete_by_agent("test_agent")
        await vm.close()

