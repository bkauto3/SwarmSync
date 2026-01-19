"""
ReasoningBank - Shared Memory & Collective Intelligence System (FIXED)
Layer 6 implementation for Genesis multi-agent system

FIXES APPLIED:
- MongoDB injection vulnerability (regex escaping)
- Enum serialization bug (convert to values)
- Resource cleanup (context manager)
- Race conditions (atomic updates)
- Cache invalidation (proper TTL management)
- Thread-safe singleton
- Input validation
- Database indexes

Three-tier memory system:
1. Consensus Memory: Verified team procedures and successful patterns
2. Persona Library: Agent characteristics, specializations, performance metrics
3. Whiteboard Memory: Shared working spaces for collaborative tasks
"""

import json
import re
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    logger.warning("MongoDB not available - using in-memory storage")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - using in-memory cache")


class MemoryType(Enum):
    """Types of memory in the ReasoningBank"""
    CONSENSUS = "consensus"
    PERSONA = "persona"
    WHITEBOARD = "whiteboard"
    STRATEGY = "strategy"


class OutcomeTag(Enum):
    """Outcome tags for contrastive evaluation"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass(frozen=True)  # FIX: Immutable for database records
class MemoryEntry:
    """Base memory entry structure"""
    memory_id: str
    memory_type: str  # FIX: Store as string, not Enum
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    outcome: str  # FIX: Store as string, not Enum
    win_rate: float
    usage_count: int
    created_at: str
    updated_at: str
    tags: tuple  # FIX: Tuple for frozen dataclass


@dataclass(frozen=True)
class StrategyNugget:
    """Distilled strategy from successful/failed trajectories"""
    strategy_id: str
    description: str
    context: str
    task_metadata: Dict[str, Any]
    environment: str
    tools_used: tuple  # FIX: Tuple for frozen
    outcome: str  # FIX: String not Enum
    win_rate: float
    steps: tuple  # FIX: Tuple for frozen
    learned_from: tuple  # FIX: Tuple for frozen
    created_at: str
    usage_count: int = 0
    successes: int = 0


@dataclass(frozen=True)
class AgentPersona:
    """Agent characteristics and specializations"""
    agent_id: str
    agent_name: str
    specialization: str
    capabilities: tuple  # FIX: Tuple for frozen
    success_rate: float
    total_tasks: int
    successful_tasks: int
    average_cost: float
    preferred_models: tuple  # FIX: Tuple for frozen
    performance_metrics: Dict[str, float]
    created_at: str
    updated_at: str


class ReasoningBank:
    """
    Shared memory system for multi-agent collective intelligence

    FIXED: Thread-safe, resource cleanup, security hardening
    """

    # Constants (FIX: No magic numbers)
    MONGO_TIMEOUT_MS = 5000
    REDIS_CACHE_TTL_SECONDS = 3600
    STRATEGY_PRUNE_THRESHOLD = 0.3
    MAX_IN_MEMORY_ENTRIES = 10000

    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017/",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        db_name: str = "genesis_reasoning_bank"
    ):
        self.db_name = db_name
        self.in_memory_store: Dict[str, MemoryEntry] = {}
        self.in_memory_strategies: Dict[str, StrategyNugget] = {}
        self.in_memory_personas: Dict[str, AgentPersona] = {}
        self._lock = threading.Lock()  # FIX: Thread safety

        self.mongo_client = None
        self.redis_client = None
        self.mongo_available = False
        self.redis_available = False

        # MongoDB setup with proper error handling
        if MONGO_AVAILABLE:
            try:
                self.mongo_client = MongoClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=self.MONGO_TIMEOUT_MS,
                    maxPoolSize=50,  # FIX: Connection pooling
                    minPoolSize=10
                )
                # Test connection
                self.mongo_client.admin.command('ping')
                self.db = self.mongo_client[db_name]
                self.memories = self.db.memories
                self.strategies = self.db.strategies
                self.personas = self.db.personas

                # FIX: Create indexes for performance
                self._create_indexes()

                self.mongo_available = True
                logger.info(f"✅ ReasoningBank connected to MongoDB: {db_name}")
            except (ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError) as e:
                logger.warning(f"MongoDB connection failed: {e}")
                logger.info("Using in-memory storage instead")
                self.mongo_available = False

        # Redis setup with proper error handling
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True,
                    socket_connect_timeout=5
                )
                self.redis_client.ping()
                self.redis_available = True
                logger.info("✅ ReasoningBank connected to Redis cache")
            except redis.ConnectionError as e:
                logger.warning(f"Redis connection failed: {e}")
                logger.info("Caching disabled")
                self.redis_available = False

    def _create_indexes(self):
        """FIX: Create database indexes for performance"""
        try:
            # Memory indexes
            self.memories.create_index([("memory_id", 1)], unique=True)
            self.memories.create_index([("memory_type", 1)])
            self.memories.create_index([("tags", 1)])
            self.memories.create_index([("win_rate", -1)])
            self.memories.create_index([("created_at", -1)])

            # Strategy indexes
            self.strategies.create_index([("strategy_id", 1)], unique=True)
            self.strategies.create_index([("context", "text"), ("description", "text")])  # Text search
            self.strategies.create_index([("win_rate", -1)])

            # Persona indexes
            self.personas.create_index([("agent_id", 1)], unique=True)

            logger.info("✅ Database indexes created")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")

    # FIX: Context manager for resource cleanup
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):
        """Clean up connections"""
        if self.mongo_available and self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB connection closed")
        if self.redis_available and self.redis_client:
            self.redis_client.close()
            logger.info("Redis connection closed")

    def __del__(self):
        """Ensure cleanup on garbage collection"""
        try:
            self.close()
        except Exception:
            pass

    def _generate_id(self, content: str = None) -> str:
        """Generate unique ID - FIX: Full hash or UUID"""
        if content:
            # Deterministic for deduplication
            return hashlib.sha256(content.encode()).hexdigest()  # Full hash
        else:
            # Random for new entries
            return str(uuid.uuid4())

    def _entry_to_dict(self, entry: MemoryEntry) -> Dict[str, Any]:
        """FIX: Convert entry to dict with proper serialization"""
        return {
            "memory_id": entry.memory_id,
            "memory_type": entry.memory_type,  # Already string
            "content": entry.content,
            "metadata": entry.metadata,
            "outcome": entry.outcome,  # Already string
            "win_rate": entry.win_rate,
            "usage_count": entry.usage_count,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "tags": list(entry.tags)  # Convert tuple to list for JSON
        }

    def _strategy_to_dict(self, strategy: StrategyNugget) -> Dict[str, Any]:
        """FIX: Convert strategy to dict with proper serialization"""
        return {
            "strategy_id": strategy.strategy_id,
            "description": strategy.description,
            "context": strategy.context,
            "task_metadata": strategy.task_metadata,
            "environment": strategy.environment,
            "tools_used": list(strategy.tools_used),
            "outcome": strategy.outcome,  # Already string
            "win_rate": strategy.win_rate,
            "steps": list(strategy.steps),
            "learned_from": list(strategy.learned_from),
            "created_at": strategy.created_at,
            "usage_count": strategy.usage_count,
            "successes": strategy.successes
        }

    def _validate_inputs(self, task_context: str, top_n: int, min_win_rate: float):
        """FIX: Input validation"""
        if not task_context or not task_context.strip():
            raise ValueError("task_context cannot be empty")
        if top_n < 1:
            raise ValueError(f"top_n must be >= 1, got {top_n}")
        if not 0.0 <= min_win_rate <= 1.0:
            raise ValueError(f"min_win_rate must be in [0.0, 1.0], got {min_win_rate}")

    def store_memory(
        self,
        memory_type: MemoryType,
        content: Dict[str, Any],
        metadata: Dict[str, Any],
        outcome: OutcomeTag = OutcomeTag.UNKNOWN,
        tags: List[str] = None
    ) -> str:
        """Store a memory entry"""
        memory_id = self._generate_id(json.dumps(content, sort_keys=True))
        now = datetime.now(timezone.utc).isoformat()

        entry = MemoryEntry(
            memory_id=memory_id,
            memory_type=memory_type.value,  # FIX: Store as string
            content=content,
            metadata=metadata,
            outcome=outcome.value,  # FIX: Store as string
            win_rate=0.0,
            usage_count=0,
            created_at=now,
            updated_at=now,
            tags=tuple(tags or [])  # FIX: Tuple for frozen
        )

        if self.mongo_available:
            self.memories.insert_one(self._entry_to_dict(entry))
        else:
            # FIX: Thread-safe in-memory storage
            with self._lock:
                self.in_memory_store[memory_id] = entry

        # Cache in Redis
        if self.redis_available:
            try:
                self.redis_client.setex(
                    f"memory:{memory_id}",
                    self.REDIS_CACHE_TTL_SECONDS,
                    json.dumps(self._entry_to_dict(entry))
                )
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")

        return memory_id

    def store_strategy(
        self,
        description: str,
        context: str,
        task_metadata: Dict[str, Any],
        environment: str,
        tools_used: List[str],
        outcome: OutcomeTag,
        steps: List[str],
        learned_from: List[str]
    ) -> str:
        """Store a distilled strategy nugget"""
        strategy_id = self._generate_id(f"{description}:{context}")
        now = datetime.now(timezone.utc).isoformat()

        strategy = StrategyNugget(
            strategy_id=strategy_id,
            description=description,
            context=context,
            task_metadata=task_metadata,
            environment=environment,
            tools_used=tuple(tools_used),  # FIX: Tuple for frozen
            outcome=outcome.value,  # FIX: String
            win_rate=0.0,
            steps=tuple(steps),  # FIX: Tuple
            learned_from=tuple(learned_from),  # FIX: Tuple
            created_at=now,
            usage_count=0,
            successes=0
        )

        if self.mongo_available:
            self.strategies.insert_one(self._strategy_to_dict(strategy))
        else:
            with self._lock:
                self.in_memory_strategies[strategy_id] = strategy

        return strategy_id

    def store_persona(self, persona: AgentPersona) -> str:
        """Store or update agent persona"""
        persona_dict = asdict(persona)
        # Convert tuples to lists for JSON
        persona_dict['capabilities'] = list(persona_dict['capabilities'])
        persona_dict['preferred_models'] = list(persona_dict['preferred_models'])

        if self.mongo_available:
            self.personas.update_one(
                {"agent_id": persona.agent_id},
                {"$set": persona_dict},
                upsert=True
            )
        else:
            with self._lock:
                self.in_memory_personas[persona.agent_id] = persona

        return persona.agent_id

    def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry"""
        # Check Redis cache first
        if self.redis_available:
            try:
                cached = self.redis_client.get(f"memory:{memory_id}")
                if cached:
                    data = json.loads(cached)
                    data['tags'] = tuple(data['tags'])
                    return MemoryEntry(**data)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")

        # Check MongoDB
        if self.mongo_available:
            data = self.memories.find_one({"memory_id": memory_id})
            if data:
                data.pop('_id', None)
                data['tags'] = tuple(data['tags'])
                return MemoryEntry(**data)
        else:
            return self.in_memory_store.get(memory_id)

        return None

    def search_strategies(
        self,
        task_context: str,
        top_n: int = 5,
        min_win_rate: float = 0.0  # FIX: Default to 0.0 for cold start
    ) -> List[StrategyNugget]:
        """
        Search for relevant strategies (MaTTS pattern)
        FIX: Input validation, SQL injection prevention
        """
        # FIX: Validate inputs
        self._validate_inputs(task_context, top_n, min_win_rate)

        if self.mongo_available:
            try:
                # FIX: Use text search instead of regex (safer and faster)
                results = self.strategies.find(
                    {
                        "$text": {"$search": task_context},
                        "win_rate": {"$gte": min_win_rate}
                    },
                    {"score": {"$meta": "textScore"}}
                ).sort([("score", {"$meta": "textScore"}), ("win_rate", -1)]).limit(top_n)

                strategies = []
                for data in results:
                    data.pop('_id', None)
                    # Convert lists back to tuples
                    data['tools_used'] = tuple(data.get('tools_used', []))
                    data['steps'] = tuple(data.get('steps', []))
                    data['learned_from'] = tuple(data.get('learned_from', []))
                    strategies.append(StrategyNugget(**data))
                return strategies
            except Exception as e:
                logger.warning(f"Text search failed, falling back to in-memory: {e}")
                # Fallback to in-memory

        # In-memory search
        with self._lock:
            matched = [
                s for s in self.in_memory_strategies.values()
                if task_context.lower() in s.context.lower() and s.win_rate >= min_win_rate
            ]
        return sorted(matched, key=lambda x: x.win_rate, reverse=True)[:top_n]

    def update_strategy_outcome(self, strategy_id: str, success: bool):
        """FIX: Atomic update to prevent race conditions"""
        if self.mongo_available:
            # FIX: Use atomic operations
            self.strategies.update_one(
                {"strategy_id": strategy_id},
                {
                    "$inc": {
                        "usage_count": 1,
                        "successes": 1 if success else 0
                    },
                    "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
                }
            )

            # Calculate win_rate separately (can't do atomically with MongoDB)
            strategy_data = self.strategies.find_one({"strategy_id": strategy_id})
            if strategy_data:
                usage_count = strategy_data.get('usage_count', 1)
                successes = strategy_data.get('successes', 0)
                win_rate = successes / usage_count if usage_count > 0 else 0.0
                self.strategies.update_one(
                    {"strategy_id": strategy_id},
                    {"$set": {"win_rate": win_rate}}
                )

            # FIX: Invalidate cache
            if self.redis_available:
                try:
                    self.redis_client.delete(f"strategy:{strategy_id}")
                except Exception as e:
                    logger.warning(f"Cache invalidation failed: {e}")
        else:
            # FIX: Thread-safe in-memory update
            with self._lock:
                if strategy_id in self.in_memory_strategies:
                    old_strategy = self.in_memory_strategies[strategy_id]
                    usage_count = old_strategy.usage_count + 1
                    successes = old_strategy.successes + (1 if success else 0)
                    win_rate = successes / usage_count

                    # Create new frozen instance
                    from dataclasses import replace
                    updated_strategy = replace(
                        old_strategy,
                        usage_count=usage_count,
                        successes=successes,
                        win_rate=win_rate
                    )
                    self.in_memory_strategies[strategy_id] = updated_strategy

    def get_agent_persona(self, agent_id: str) -> Optional[AgentPersona]:
        """Retrieve agent persona"""
        if self.mongo_available:
            data = self.personas.find_one({"agent_id": agent_id})
            if data:
                data.pop('_id', None)
                # Convert lists to tuples
                data['capabilities'] = tuple(data.get('capabilities', []))
                data['preferred_models'] = tuple(data.get('preferred_models', []))
                return AgentPersona(**data)
        else:
            return self.in_memory_personas.get(agent_id)

        return None

    def prune_low_performing_strategies(self, threshold: float = None):
        """Remove strategies with win rates below threshold"""
        threshold = threshold or self.STRATEGY_PRUNE_THRESHOLD

        if self.mongo_available:
            result = self.strategies.delete_many({"win_rate": {"$lt": threshold}})
            logger.info(f"🗑️  Pruned {result.deleted_count} low-performing strategies (< {threshold} win rate)")
        else:
            with self._lock:
                before = len(self.in_memory_strategies)
                self.in_memory_strategies = {
                    k: v for k, v in self.in_memory_strategies.items()
                    if v.win_rate >= threshold
                }
                pruned = before - len(self.in_memory_strategies)
            logger.info(f"🗑️  Pruned {pruned} low-performing strategies (< {threshold} win rate)")

    def get_consensus_memory(self, tags: List[str] = None) -> List[MemoryEntry]:
        """Get consensus memories (verified procedures)"""
        query = {"memory_type": MemoryType.CONSENSUS.value}
        if tags:
            query["tags"] = {"$in": tags}

        if self.mongo_available:
            results = self.memories.find(query).sort("win_rate", -1)
            memories = []
            for data in results:
                data.pop('_id', None)
                data['tags'] = tuple(data.get('tags', []))
                memories.append(MemoryEntry(**data))
            return memories
        else:
            with self._lock:
                return [
                    m for m in self.in_memory_store.values()
                    if m.memory_type == MemoryType.CONSENSUS.value and
                    (not tags or any(t in m.tags for t in tags))
                ]


# FIX: Thread-safe singleton
_reasoning_bank_instance: Optional[ReasoningBank] = None
_reasoning_bank_lock = threading.Lock()


def get_reasoning_bank() -> ReasoningBank:
    """Get or create ReasoningBank singleton (thread-safe)"""
    global _reasoning_bank_instance

    if _reasoning_bank_instance is None:
        with _reasoning_bank_lock:
            # Double-check locking
            if _reasoning_bank_instance is None:
                _reasoning_bank_instance = ReasoningBank()

    return _reasoning_bank_instance
