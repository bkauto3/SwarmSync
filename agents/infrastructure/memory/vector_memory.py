"""
Vector Memory for Genesis Layer 6 Memory

Provides semantic search over agent interactions using TEI embeddings + MongoDB.

Key Features:
- TEI embeddings (768-dim, 64x cheaper than OpenAI)
- MongoDB Atlas Vector Search
- Agent interaction storage with metadata
- Similarity search with filtering
- Batch operations for efficiency
- OTEL observability

Architecture:
- Embeddings: TEI (BAAI/bge-base-en-v1.5, 768 dimensions)
- Storage: MongoDB with vector indexes
- Search: Cosine similarity via MongoDB $vectorSearch
- Metadata: Agent ID, timestamp, business type, tags

Performance Targets:
- Store: <100ms P95
- Search: <200ms P95 (top-10 results)
- Throughput: 100+ operations/sec

Cost Savings:
- OpenAI embeddings: $720/month (1000 businesses)
- TEI embeddings: $1.12/month
- Savings: $718.88/month ($8,626/year)

Integration Points:
- AgenticRAG: Hybrid vector-graph retrieval
- CaseBank: Similarity search over trajectories
- All 15 agents: Store/retrieve past interactions

Usage:
    vm = VectorMemory()
    await vm.connect()
    
    # Store interaction
    await vm.store_interaction(
        agent_id="qa_agent",
        interaction="Fixed Stripe checkout bug",
        metadata={"business_type": "ecommerce"}
    )
    
    # Search similar
    results = await vm.search_similar(
        query="Payment integration issue",
        limit=5
    )

Author: Cora (Integration Lead)
Date: November 4, 2025
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

import numpy as np
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, OperationFailure

from infrastructure.tei_client import get_tei_client
from infrastructure.logging_config import get_logger
from infrastructure.observability import (
    get_observability_manager,
    SpanType,
)

logger = get_logger(__name__)
obs_manager = get_observability_manager()


@dataclass
class VectorMemoryStats:
    """Statistics for vector memory operations."""
    total_stores: int = 0
    total_searches: int = 0
    total_embeddings_generated: int = 0
    avg_search_latency_ms: float = 0.0
    errors: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_stores": self.total_stores,
            "total_searches": self.total_searches,
            "total_embeddings_generated": self.total_embeddings_generated,
            "avg_search_latency_ms": self.avg_search_latency_ms,
            "errors": self.errors
        }


class VectorMemory:
    """
    Vector memory for semantic search over agent interactions.
    
    Uses TEI embeddings + MongoDB Atlas Vector Search for efficient
    similarity-based retrieval of past agent experiences.
    
    Features:
    - Store agent interactions with embeddings
    - Similarity search with metadata filtering
    - Batch operations for efficiency
    - Automatic index creation
    - OTEL observability
    
    Usage:
        vm = VectorMemory()
        await vm.connect()
        
        # Store
        await vm.store_interaction(
            agent_id="builder_agent",
            interaction="Created Next.js app with Stripe",
            metadata={"business_type": "saas"}
        )
        
        # Search
        results = await vm.search_similar(
            query="How to integrate Stripe?",
            agent_id="builder_agent",
            limit=5
        )
    """
    
    def __init__(
        self,
        mongodb_uri: str = None,
        database_name: str = "genesis_memory",
        collection_name: str = "agent_interactions",
        embedding_dim: int = 768,
        enable_otel: bool = True
    ):
        """
        Initialize VectorMemory.
        
        Args:
            mongodb_uri: MongoDB connection URI
            database_name: Database name
            collection_name: Collection name
            embedding_dim: Embedding dimensionality (768 for bge-base)
            enable_otel: Enable OpenTelemetry tracing
        """
        self.mongodb_uri = mongodb_uri or os.getenv(
            "MONGODB_URI",
            "mongodb://localhost:27017"
        )
        self.database_name = database_name
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.enable_otel = enable_otel
        
        # MongoDB client (initialized in connect())
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.collection = None
        
        # TEI client
        self.tei = get_tei_client()
        
        # Statistics
        self.stats = VectorMemoryStats()
        
        # Connection state
        self._connected = False
        
        logger.info(
            f"VectorMemory initialized: db={database_name}, "
            f"collection={collection_name}, dim={embedding_dim}"
        )
    
    async def connect(self):
        """Connect to MongoDB and create indexes."""
        if self._connected:
            return
        
        try:
            # Connect to MongoDB
            self.client = AsyncIOMotorClient(
                self.mongodb_uri,
                maxPoolSize=50,
                minPoolSize=10,
                serverSelectionTimeoutMS=5000
            )
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Get database and collection
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            # Create indexes
            await self._create_indexes()
            
            self._connected = True
            logger.info(f"VectorMemory connected to MongoDB: {self.mongodb_uri}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def _create_indexes(self):
        """Create MongoDB indexes for efficient queries."""
        try:
            # Create compound index for metadata filtering
            await self.collection.create_index([
                ("agent_id", 1),
                ("timestamp", -1)
            ])
            
            # Create index for business type filtering
            await self.collection.create_index([
                ("metadata.business_type", 1)
            ])
            
            logger.info("VectorMemory indexes created")
            
            # Note: Vector search index must be created via MongoDB Atlas UI
            # See: https://www.mongodb.com/docs/atlas/atlas-vector-search/create-index/
            logger.warning(
                "Vector search index must be created manually in MongoDB Atlas. "
                "Index name: 'embedding_index', path: 'embedding', dimensions: 768, "
                "similarity: 'cosine'"
            )
            
        except Exception as e:
            logger.warning(f"Failed to create indexes: {e}")
    
    async def store_interaction(
        self,
        agent_id: str,
        interaction: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Store agent interaction with embedding.
        
        Args:
            agent_id: Agent identifier (e.g., "qa_agent")
            interaction: Interaction text
            metadata: Additional metadata (business_type, tags, etc.)
        
        Returns:
            Interaction ID
        """
        if not self._connected:
            await self.connect()
        
        with obs_manager.timed_operation(
            "vector_memory.store_interaction",
            SpanType.EXECUTION
        ) as span:
            span.set_attribute("agent_id", agent_id)
            span.set_attribute("interaction_length", len(interaction))
            
            try:
                # Generate embedding
                embedding = await self.tei.embed_single(interaction)
                
                # Create document
                doc = {
                    "agent_id": agent_id,
                    "interaction": interaction,
                    "embedding": embedding.tolist(),
                    "metadata": metadata or {},
                    "timestamp": datetime.now(timezone.utc)
                }
                
                # Insert into MongoDB
                result = await self.collection.insert_one(doc)
                
                # Update statistics
                self.stats.total_stores += 1
                self.stats.total_embeddings_generated += 1
                
                span.set_attribute("interaction_id", str(result.inserted_id))
                span.set_attribute("success", True)
                
                logger.debug(
                    f"Stored interaction: agent={agent_id}, "
                    f"id={result.inserted_id}"
                )
                
                return str(result.inserted_id)
                
            except Exception as e:
                self.stats.errors += 1
                span.set_attribute("error", str(e))
                logger.error(f"Failed to store interaction: {e}")
                raise
    
    async def search_similar(
        self,
        query: str,
        limit: int = 10,
        agent_id: str = None,
        business_type: str = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar interactions using vector similarity.
        
        Args:
            query: Query text
            limit: Maximum number of results
            agent_id: Filter by agent ID (optional)
            business_type: Filter by business type (optional)
            min_score: Minimum similarity score (0.0-1.0)
        
        Returns:
            List of matching interactions with scores
        """
        if not self._connected:
            await self.connect()
        
        with obs_manager.timed_operation(
            "vector_memory.search_similar",
            SpanType.EXECUTION
        ) as span:
            span.set_attribute("query_length", len(query))
            span.set_attribute("limit", limit)
            span.set_attribute("agent_id", agent_id or "all")
            
            try:
                # Generate query embedding
                query_embedding = await self.tei.embed_single(query)
                
                # Build MongoDB aggregation pipeline
                pipeline = []
                
                # Vector search stage
                pipeline.append({
                    "$vectorSearch": {
                        "index": "embedding_index",
                        "path": "embedding",
                        "queryVector": query_embedding.tolist(),
                        "numCandidates": limit * 10,  # Oversampling for better results
                        "limit": limit
                    }
                })
                
                # Add score to results
                pipeline.append({
                    "$addFields": {
                        "score": {"$meta": "vectorSearchScore"}
                    }
                })
                
                # Filter by agent_id if specified
                if agent_id:
                    pipeline.append({
                        "$match": {"agent_id": agent_id}
                    })
                
                # Filter by business_type if specified
                if business_type:
                    pipeline.append({
                        "$match": {"metadata.business_type": business_type}
                    })
                
                # Filter by minimum score
                if min_score > 0.0:
                    pipeline.append({
                        "$match": {"score": {"$gte": min_score}}
                    })
                
                # Execute aggregation
                cursor = self.collection.aggregate(pipeline)
                results = await cursor.to_list(length=limit)
                
                # Update statistics
                self.stats.total_searches += 1
                self.stats.total_embeddings_generated += 1
                
                span.set_attribute("num_results", len(results))
                span.set_attribute("success", True)
                
                logger.debug(
                    f"Vector search: query='{query[:50]}...', "
                    f"results={len(results)}"
                )
                
                return results
                
            except Exception as e:
                self.stats.errors += 1
                span.set_attribute("error", str(e))
                logger.error(f"Vector search failed: {e}")
                
                # Return empty list on error (graceful degradation)
                return []

    async def store_batch(
        self,
        interactions: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Store multiple interactions in batch.

        Args:
            interactions: List of dicts with 'agent_id', 'interaction', 'metadata'

        Returns:
            List of interaction IDs
        """
        if not self._connected:
            await self.connect()

        if not interactions:
            return []

        with obs_manager.timed_operation(
            "vector_memory.store_batch",
            SpanType.EXECUTION
        ) as span:
            span.set_attribute("batch_size", len(interactions))

            try:
                # Extract texts for batch embedding
                texts = [item["interaction"] for item in interactions]

                # Generate embeddings in batch
                embeddings = await self.tei.embed_batch(texts)

                # Create documents
                docs = []
                for i, item in enumerate(interactions):
                    docs.append({
                        "agent_id": item["agent_id"],
                        "interaction": item["interaction"],
                        "embedding": embeddings[i].tolist(),
                        "metadata": item.get("metadata", {}),
                        "timestamp": datetime.now(timezone.utc)
                    })

                # Insert batch
                result = await self.collection.insert_many(docs)

                # Update statistics
                self.stats.total_stores += len(interactions)
                self.stats.total_embeddings_generated += len(interactions)

                span.set_attribute("success", True)

                logger.info(f"Stored {len(interactions)} interactions in batch")

                return [str(id) for id in result.inserted_ids]

            except Exception as e:
                self.stats.errors += 1
                span.set_attribute("error", str(e))
                logger.error(f"Batch store failed: {e}")
                raise

    async def get_by_id(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get interaction by ID.

        Args:
            interaction_id: Interaction ID

        Returns:
            Interaction document or None
        """
        if not self._connected:
            await self.connect()

        try:
            from bson import ObjectId
            result = await self.collection.find_one({"_id": ObjectId(interaction_id)})
            return result
        except Exception as e:
            logger.error(f"Failed to get interaction by ID: {e}")
            return None

    async def delete_by_agent(self, agent_id: str) -> int:
        """
        Delete all interactions for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Number of deleted documents
        """
        if not self._connected:
            await self.connect()

        try:
            result = await self.collection.delete_many({"agent_id": agent_id})
            logger.info(f"Deleted {result.deleted_count} interactions for {agent_id}")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Failed to delete interactions: {e}")
            return 0

    def get_stats(self) -> VectorMemoryStats:
        """Get statistics."""
        return self.stats

    def reset_stats(self):
        """Reset statistics."""
        self.stats = VectorMemoryStats()

    async def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("VectorMemory connection closed")


# Singleton instance
_vector_memory: Optional[VectorMemory] = None


def get_vector_memory(**kwargs) -> VectorMemory:
    """
    Get singleton VectorMemory instance.

    Args:
        **kwargs: Arguments for VectorMemory

    Returns:
        VectorMemory instance
    """
    global _vector_memory

    if _vector_memory is None:
        _vector_memory = VectorMemory(**kwargs)

    return _vector_memory


def reset_vector_memory():
    """Reset singleton instance (for testing)."""
    global _vector_memory
    _vector_memory = None

