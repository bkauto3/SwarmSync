"""
Replay Buffer - Experience Storage for Self-Improving Agents
Layer 2 implementation for Genesis multi-agent system (Darwin Gödel Machine)

Production Features:
- Redis Streams for real-time append-only logging
- MongoDB for long-term trajectory storage with indexes
- Thread-safe concurrent access with locks
- Graceful degradation to in-memory when backends unavailable
- Random sampling for training (not just recent)
- Comprehensive statistics tracking
- Proper resource cleanup via context manager
- Input validation on all methods
- Specific exception handling

Purpose:
Captures every action agents take (trajectories) for learning from experience.
Each trajectory contains a sequence of actions, tool calls, reasoning, and outcomes.
Successful trajectories are used for positive reinforcement, failures for contrastive learning.
"""

import json
import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import OutcomeTag from ReasoningBank for consistency
try:
    from infrastructure.reasoning_bank import OutcomeTag
except ImportError:
    # Fallback if ReasoningBank not available
    class OutcomeTag(Enum):
        """Outcome tags for contrastive evaluation"""
        SUCCESS = "success"
        FAILURE = "failure"
        PARTIAL = "partial"
        UNKNOWN = "unknown"

# MongoDB support
try:
    from pymongo import MongoClient, DESCENDING
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    logger.warning("MongoDB not available - using in-memory trajectory storage")

# Redis support
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - using in-memory streaming")


@dataclass(frozen=True)
class ActionStep:
    """
    Single step in an agent trajectory

    Captures the complete context of one agent action:
    - What the agent was thinking (reasoning)
    - What action it took (tool_name + args)
    - What happened (tool_result)
    - When it happened (timestamp)
    """
    timestamp: str
    tool_name: str
    tool_args: Dict[str, Any]
    tool_result: Any
    agent_reasoning: str  # Why agent chose this action


@dataclass(frozen=True)
class Trajectory:
    """
    Complete trajectory of an agent task execution

    A trajectory is a sequence of ActionSteps from task start to completion.
    Used for:
    - Learning successful patterns (high reward)
    - Contrastive learning from failures (low reward)
    - Replay for policy improvement
    - Strategy distillation (see ReasoningBank)
    """
    trajectory_id: str
    agent_id: str
    task_description: str
    initial_state: Dict[str, Any]
    steps: tuple  # Tuple of ActionStep for immutability
    final_outcome: str  # OutcomeTag value (SUCCESS, FAILURE, PARTIAL)
    reward: float  # 0.0 to 1.0
    metadata: Dict[str, Any]
    created_at: str
    duration_seconds: float
    # Failure tracking fields (backward compatible with None defaults)
    failure_rationale: Optional[str] = None  # WHY the failure occurred
    error_category: Optional[str] = None  # Classification: "configuration", "validation", "network", "timeout", etc.
    fix_applied: Optional[str] = None  # How the issue was resolved


class ReplayBuffer:
    """
    Production-ready replay buffer for agent learning

    Storage hierarchy:
    1. Redis Streams (real-time append-only log) - fast writes
    2. MongoDB (long-term indexed storage) - fast queries
    3. In-memory fallback (when backends unavailable)

    Thread Safety:
    - All operations protected by locks
    - Atomic updates where possible

    Sampling Strategy:
    - Random sampling across all trajectories (not biased to recent)
    - Filtered sampling by outcome type
    - Top-N queries by reward/success rate
    """

    # Constants - no magic numbers
    MONGO_TIMEOUT_MS = 5000
    REDIS_STREAM_MAX_LEN = 10000  # Keep last 10k in stream
    REDIS_STREAM_KEY = "agent_trajectories"
    MAX_IN_MEMORY_TRAJECTORIES = 5000
    DEFAULT_PRUNE_DAYS = 30

    def __init__(
        self,
        mongo_uri: str = "mongodb://localhost:27017/",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        db_name: str = "genesis_replay_buffer"
    ):
        """
        Initialize ReplayBuffer with database connections

        Args:
            mongo_uri: MongoDB connection string
            redis_host: Redis server hostname
            redis_port: Redis server port
            db_name: MongoDB database name
        """
        self.db_name = db_name
        self.in_memory_trajectories: Dict[str, Trajectory] = {}
        self._lock = threading.Lock()  # Thread safety

        self.mongo_client = None
        self.redis_client = None
        self.mongo_available = False
        self.redis_available = False

        # MongoDB setup with error handling
        if MONGO_AVAILABLE:
            try:
                self.mongo_client = MongoClient(
                    mongo_uri,
                    serverSelectionTimeoutMS=self.MONGO_TIMEOUT_MS,
                    maxPoolSize=50,  # Connection pooling
                    minPoolSize=10
                )
                # Test connection
                self.mongo_client.admin.command('ping')
                self.db = self.mongo_client[db_name]
                self.trajectories = self.db.trajectories

                # Create indexes for performance
                self._create_indexes()

                self.mongo_available = True
                logger.info(f"✅ ReplayBuffer connected to MongoDB: {db_name}")
            except (ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError) as e:
                logger.warning(f"MongoDB connection failed: {e}")
                logger.info("Using in-memory trajectory storage instead")
                self.mongo_available = False

        # Redis setup with error handling
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
                logger.info("✅ ReplayBuffer connected to Redis Streams")
            except redis.ConnectionError as e:
                logger.warning(f"Redis connection failed: {e}")
                logger.info("Real-time streaming disabled")
                self.redis_available = False

    def _create_indexes(self):
        """Create database indexes for fast queries"""
        try:
            # Core indexes
            self.trajectories.create_index([("trajectory_id", 1)], unique=True)
            self.trajectories.create_index([("agent_id", 1)])
            self.trajectories.create_index([("task_description", "text")])  # Text search support (prevents regex injection)
            self.trajectories.create_index([("final_outcome", 1)])
            self.trajectories.create_index([("created_at", DESCENDING)])
            self.trajectories.create_index([("reward", DESCENDING)])

            # Compound indexes for common queries
            self.trajectories.create_index([("agent_id", 1), ("final_outcome", 1)])
            self.trajectories.create_index([("final_outcome", 1), ("reward", DESCENDING)])

            logger.info("✅ ReplayBuffer indexes created")
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")

    # Context manager for resource cleanup
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

    def _validate_trajectory(self, trajectory: Trajectory):
        """
        Validate trajectory before storage

        Raises:
            ValueError: If trajectory data is invalid
        """
        if not trajectory.trajectory_id:
            raise ValueError("trajectory_id cannot be empty")
        if not trajectory.agent_id:
            raise ValueError("agent_id cannot be empty")
        if not trajectory.task_description or not trajectory.task_description.strip():
            raise ValueError("task_description cannot be empty")
        if not 0.0 <= trajectory.reward <= 1.0:
            raise ValueError(f"reward must be in [0.0, 1.0], got {trajectory.reward}")
        if trajectory.duration_seconds < 0:
            raise ValueError(f"duration_seconds must be >= 0, got {trajectory.duration_seconds}")
        if trajectory.final_outcome not in [e.value for e in OutcomeTag]:
            raise ValueError(f"final_outcome must be one of {[e.value for e in OutcomeTag]}")

    def _trajectory_to_dict(self, trajectory: Trajectory) -> Dict[str, Any]:
        """
        Convert Trajectory to dict for storage

        Handles serialization of nested dataclasses and tuples
        """
        traj_dict = {
            "trajectory_id": trajectory.trajectory_id,
            "agent_id": trajectory.agent_id,
            "task_description": trajectory.task_description,
            "initial_state": trajectory.initial_state,
            "steps": [asdict(step) for step in trajectory.steps],  # Convert ActionSteps
            "final_outcome": trajectory.final_outcome,
            "reward": trajectory.reward,
            "metadata": trajectory.metadata,
            "created_at": trajectory.created_at,
            "duration_seconds": trajectory.duration_seconds,
            "failure_rationale": trajectory.failure_rationale,
            "error_category": trajectory.error_category,
            "fix_applied": trajectory.fix_applied
        }
        return traj_dict

    def _dict_to_trajectory(self, data: Dict[str, Any]) -> Trajectory:
        """
        Convert dict to Trajectory

        Reconstructs dataclasses from stored format
        """
        # Reconstruct ActionStep objects
        steps = tuple(ActionStep(**step) for step in data.get('steps', []))

        return Trajectory(
            trajectory_id=data['trajectory_id'],
            agent_id=data['agent_id'],
            task_description=data['task_description'],
            initial_state=data['initial_state'],
            steps=steps,
            final_outcome=data['final_outcome'],
            reward=data['reward'],
            metadata=data['metadata'],
            created_at=data['created_at'],
            duration_seconds=data['duration_seconds'],
            failure_rationale=data.get('failure_rationale'),  # Backward compatible
            error_category=data.get('error_category'),
            fix_applied=data.get('fix_applied')
        )

    def store_trajectory(self, trajectory: Trajectory) -> str:
        """
        Store a complete trajectory

        Writes to:
        1. Redis Stream (real-time log)
        2. MongoDB (persistent storage)
        3. In-memory (fallback)

        Args:
            trajectory: Trajectory object to store

        Returns:
            trajectory_id of stored trajectory

        Raises:
            ValueError: If trajectory data is invalid
        """
        # Validate input
        self._validate_trajectory(trajectory)

        traj_dict = self._trajectory_to_dict(trajectory)

        # Write to Redis Stream (append-only log)
        if self.redis_available:
            try:
                # Use XADD with MAXLEN for automatic pruning
                self.redis_client.xadd(
                    self.REDIS_STREAM_KEY,
                    {"data": json.dumps(traj_dict)},
                    maxlen=self.REDIS_STREAM_MAX_LEN,
                    approximate=True  # Faster pruning
                )
            except Exception as e:
                logger.warning(f"Redis stream write failed: {e}")

        # Write to MongoDB (persistent)
        if self.mongo_available:
            try:
                self.trajectories.insert_one(traj_dict)
            except Exception as e:
                logger.error(f"MongoDB write failed: {e}")
                # Fall through to in-memory

        # Always update in-memory (fast access)
        with self._lock:
            self.in_memory_trajectories[trajectory.trajectory_id] = trajectory

            # Prune in-memory if too large
            if len(self.in_memory_trajectories) > self.MAX_IN_MEMORY_TRAJECTORIES:
                # Remove oldest (by created_at)
                sorted_keys = sorted(
                    self.in_memory_trajectories.keys(),
                    key=lambda k: self.in_memory_trajectories[k].created_at
                )
                oldest_key = sorted_keys[0]
                del self.in_memory_trajectories[oldest_key]

        logger.info(f"✅ Stored trajectory {trajectory.trajectory_id} "
                   f"(outcome={trajectory.final_outcome}, reward={trajectory.reward:.2f})")

        # Store failure as anti-pattern in ReasoningBank if applicable
        if trajectory.final_outcome == OutcomeTag.FAILURE.value and trajectory.failure_rationale:
            try:
                from infrastructure.reasoning_bank import get_reasoning_bank
                reasoning_bank = get_reasoning_bank()
                self._store_anti_pattern(trajectory, reasoning_bank)
            except Exception as e:
                logger.warning(f"Failed to store anti-pattern in ReasoningBank: {e}")

        return trajectory.trajectory_id

    def get_trajectory(self, trajectory_id: str) -> Optional[Trajectory]:
        """
        Retrieve a single trajectory by ID

        Search order: in-memory → MongoDB

        Args:
            trajectory_id: Unique trajectory identifier

        Returns:
            Trajectory object or None if not found
        """
        # Check in-memory first (fastest)
        with self._lock:
            if trajectory_id in self.in_memory_trajectories:
                return self.in_memory_trajectories[trajectory_id]

        # Check MongoDB
        if self.mongo_available:
            try:
                data = self.trajectories.find_one({"trajectory_id": trajectory_id})
                if data:
                    data.pop('_id', None)
                    trajectory = self._dict_to_trajectory(data)

                    # Cache in memory
                    with self._lock:
                        self.in_memory_trajectories[trajectory_id] = trajectory

                    return trajectory
            except Exception as e:
                logger.error(f"MongoDB read failed: {e}")

        return None

    def sample_trajectories(
        self,
        n: int,
        outcome: Optional[OutcomeTag] = None
    ) -> List[Trajectory]:
        """
        Random sample of trajectories for training

        Uses random sampling (not biased to recent) for better learning coverage.

        Args:
            n: Number of trajectories to sample
            outcome: Optional filter by outcome (SUCCESS, FAILURE, etc.)

        Returns:
            List of sampled Trajectory objects

        Raises:
            ValueError: If n < 1
        """
        if n < 1:
            raise ValueError(f"n must be >= 1, got {n}")

        outcome_value = outcome.value if outcome else None

        # MongoDB has best sampling
        if self.mongo_available:
            try:
                query = {}
                if outcome_value:
                    query["final_outcome"] = outcome_value

                # Use aggregation pipeline for random sampling
                pipeline = [
                    {"$match": query},
                    {"$sample": {"size": n}}
                ]

                results = self.trajectories.aggregate(pipeline)
                trajectories = []
                for data in results:
                    data.pop('_id', None)
                    trajectories.append(self._dict_to_trajectory(data))

                return trajectories
            except Exception as e:
                logger.error(f"MongoDB sampling failed: {e}")
                # Fall through to in-memory

        # In-memory fallback
        with self._lock:
            all_trajectories = list(self.in_memory_trajectories.values())

        # Filter by outcome if specified
        if outcome_value:
            all_trajectories = [t for t in all_trajectories if t.final_outcome == outcome_value]

        # Random sample
        sample_size = min(n, len(all_trajectories))
        return random.sample(all_trajectories, sample_size) if sample_size > 0 else []

    def get_successful_trajectories(
        self,
        task_type: str,
        top_n: int = 10
    ) -> List[Trajectory]:
        """
        Get top successful trajectories for a task type

        Sorted by reward (highest first). Used for learning from best examples.

        Args:
            task_type: Task description substring to match
            top_n: Number of top trajectories to return

        Returns:
            List of successful Trajectory objects sorted by reward

        Raises:
            ValueError: If task_type empty or top_n < 1
        """
        if not task_type or not task_type.strip():
            raise ValueError("task_type cannot be empty")
        if top_n < 1:
            raise ValueError(f"top_n must be >= 1, got {top_n}")

        if self.mongo_available:
            try:
                # Use text search to prevent injection (safe alternative to regex)
                # Note: Requires text index on task_description field
                query = {
                    "$text": {"$search": task_type},
                    "final_outcome": OutcomeTag.SUCCESS.value
                }

                results = self.trajectories.find(query).sort("reward", DESCENDING).limit(top_n)
                trajectories = []
                for data in results:
                    data.pop('_id', None)
                    trajectories.append(self._dict_to_trajectory(data))

                return trajectories
            except Exception as e:
                logger.error(f"MongoDB query failed: {e}")
                # Fall through

        # In-memory fallback
        with self._lock:
            matched = [
                t for t in self.in_memory_trajectories.values()
                if task_type.lower() in t.task_description.lower()
                and t.final_outcome == OutcomeTag.SUCCESS.value
            ]

        # Sort by reward descending
        matched.sort(key=lambda t: t.reward, reverse=True)
        return matched[:top_n]

    def get_failed_trajectories(
        self,
        task_type: str,
        top_n: int = 10
    ) -> List[Trajectory]:
        """
        Get failed trajectories for a task type

        Used for contrastive learning - learn what NOT to do.
        Sorted by creation time (most recent first).

        Args:
            task_type: Task description substring to match
            top_n: Number of trajectories to return

        Returns:
            List of failed Trajectory objects sorted by recency

        Raises:
            ValueError: If task_type empty or top_n < 1
        """
        if not task_type or not task_type.strip():
            raise ValueError("task_type cannot be empty")
        if top_n < 1:
            raise ValueError(f"top_n must be >= 1, got {top_n}")

        if self.mongo_available:
            try:
                # Use text search to prevent injection (safe alternative to regex)
                # Note: Requires text index on task_description field
                query = {
                    "$text": {"$search": task_type},
                    "final_outcome": OutcomeTag.FAILURE.value
                }

                results = self.trajectories.find(query).sort("created_at", DESCENDING).limit(top_n)
                trajectories = []
                for data in results:
                    data.pop('_id', None)
                    trajectories.append(self._dict_to_trajectory(data))

                return trajectories
            except Exception as e:
                logger.error(f"MongoDB query failed: {e}")
                # Fall through

        # In-memory fallback
        with self._lock:
            matched = [
                t for t in self.in_memory_trajectories.values()
                if task_type.lower() in t.task_description.lower()
                and t.final_outcome == OutcomeTag.FAILURE.value
            ]

        # Sort by created_at descending (most recent first)
        matched.sort(key=lambda t: t.created_at, reverse=True)
        return matched[:top_n]

    def prune_old_trajectories(self, days_old: int = None):
        """
        Remove trajectories older than specified days

        Keeps buffer size manageable and focuses on recent experience.

        Args:
            days_old: Age threshold in days (default: 30)
        """
        days_old = days_old or self.DEFAULT_PRUNE_DAYS
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        cutoff_iso = cutoff_date.isoformat()

        if self.mongo_available:
            try:
                result = self.trajectories.delete_many({"created_at": {"$lt": cutoff_iso}})
                logger.info(f"🗑️  Pruned {result.deleted_count} trajectories older than {days_old} days")
            except Exception as e:
                logger.error(f"MongoDB pruning failed: {e}")

        # In-memory pruning
        with self._lock:
            before = len(self.in_memory_trajectories)
            self.in_memory_trajectories = {
                k: v for k, v in self.in_memory_trajectories.items()
                if v.created_at >= cutoff_iso
            }
            pruned = before - len(self.in_memory_trajectories)

        logger.info(f"🗑️  Pruned {pruned} in-memory trajectories older than {days_old} days")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive replay buffer statistics

        Returns detailed metrics for monitoring and analysis:
        - Total trajectories
        - Breakdown by outcome
        - Success rate by agent
        - Average rewards
        - Task type distribution

        Returns:
            Dictionary with statistics
        """
        stats = {
            "total_trajectories": 0,
            "by_outcome": {},
            "by_agent": {},
            "avg_reward": 0.0,
            "avg_duration_seconds": 0.0,
            "task_types": {},
            "storage_backend": "in-memory"
        }

        if self.mongo_available:
            try:
                stats["storage_backend"] = "mongodb"

                # Total count
                stats["total_trajectories"] = self.trajectories.count_documents({})

                # By outcome
                for outcome in OutcomeTag:
                    count = self.trajectories.count_documents({"final_outcome": outcome.value})
                    stats["by_outcome"][outcome.value] = count

                # By agent (aggregation)
                agent_pipeline = [
                    {"$group": {
                        "_id": "$agent_id",
                        "count": {"$sum": 1},
                        "avg_reward": {"$avg": "$reward"},
                        "success_count": {
                            "$sum": {
                                "$cond": [{"$eq": ["$final_outcome", OutcomeTag.SUCCESS.value]}, 1, 0]
                            }
                        }
                    }}
                ]
                agent_results = self.trajectories.aggregate(agent_pipeline)
                for doc in agent_results:
                    agent_id = doc["_id"]
                    total = doc["count"]
                    successes = doc["success_count"]
                    stats["by_agent"][agent_id] = {
                        "total": total,
                        "successes": successes,
                        "success_rate": successes / total if total > 0 else 0.0,
                        "avg_reward": doc["avg_reward"]
                    }

                # Global averages
                avg_pipeline = [
                    {"$group": {
                        "_id": None,
                        "avg_reward": {"$avg": "$reward"},
                        "avg_duration": {"$avg": "$duration_seconds"}
                    }}
                ]
                avg_results = list(self.trajectories.aggregate(avg_pipeline))
                if avg_results:
                    stats["avg_reward"] = avg_results[0].get("avg_reward", 0.0)
                    stats["avg_duration_seconds"] = avg_results[0].get("avg_duration", 0.0)

                return stats
            except Exception as e:
                logger.error(f"MongoDB statistics failed: {e}")
                # Fall through to in-memory

        # In-memory statistics
        with self._lock:
            trajectories = list(self.in_memory_trajectories.values())

        stats["total_trajectories"] = len(trajectories)

        if len(trajectories) == 0:
            return stats

        # By outcome
        for outcome in OutcomeTag:
            count = sum(1 for t in trajectories if t.final_outcome == outcome.value)
            stats["by_outcome"][outcome.value] = count

        # By agent
        agent_data = {}
        for traj in trajectories:
            agent_id = traj.agent_id
            if agent_id not in agent_data:
                agent_data[agent_id] = {"total": 0, "successes": 0, "rewards": []}

            agent_data[agent_id]["total"] += 1
            if traj.final_outcome == OutcomeTag.SUCCESS.value:
                agent_data[agent_id]["successes"] += 1
            agent_data[agent_id]["rewards"].append(traj.reward)

        for agent_id, data in agent_data.items():
            total = data["total"]
            successes = data["successes"]
            stats["by_agent"][agent_id] = {
                "total": total,
                "successes": successes,
                "success_rate": successes / total if total > 0 else 0.0,
                "avg_reward": sum(data["rewards"]) / len(data["rewards"]) if data["rewards"] else 0.0
            }

        # Global averages
        stats["avg_reward"] = sum(t.reward for t in trajectories) / len(trajectories)
        stats["avg_duration_seconds"] = sum(t.duration_seconds for t in trajectories) / len(trajectories)

        return stats

    def _store_anti_pattern(self, trajectory: Trajectory, reasoning_bank) -> str:
        """
        Store failure trajectory as anti-pattern in ReasoningBank

        Args:
            trajectory: Failed trajectory to store
            reasoning_bank: ReasoningBank instance

        Returns:
            Strategy ID of stored anti-pattern
        """
        from infrastructure.reasoning_bank import OutcomeTag as RBOutcomeTag

        # Extract task type from task description
        task_type = trajectory.task_description.split()[0].lower() if trajectory.task_description else "unknown"

        # Create anti-pattern description
        description = f"Anti-pattern: {trajectory.failure_rationale}"
        context = f"{task_type} task failure"

        # Create steps from ActionSteps
        steps = [
            f"{step.tool_name}({step.tool_args}) -> {step.tool_result}"
            for step in trajectory.steps
        ]

        strategy_id = reasoning_bank.store_strategy(
            description=description,
            context=context,
            task_metadata={
                "task_description": trajectory.task_description,
                "error_category": trajectory.error_category or "unknown",
                "fix_applied": trajectory.fix_applied,
                "agent_id": trajectory.agent_id,
                "trajectory_id": trajectory.trajectory_id,
                "is_anti_pattern": True  # Mark as anti-pattern
            },
            environment="production",
            tools_used=[step.tool_name for step in trajectory.steps],
            outcome=RBOutcomeTag.FAILURE,
            steps=steps,
            learned_from=[trajectory.trajectory_id]
        )

        logger.info(f"✅ Stored anti-pattern {strategy_id} from trajectory {trajectory.trajectory_id}")
        return strategy_id

    def query_anti_patterns(self, task_type: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Query anti-patterns for a specific task type from ReasoningBank

        Args:
            task_type: Type of task to query anti-patterns for
            top_n: Maximum number of anti-patterns to return

        Returns:
            List of anti-pattern dictionaries with rationale, category, and fix
        """
        try:
            from infrastructure.reasoning_bank import get_reasoning_bank

            reasoning_bank = get_reasoning_bank()

            # Search for strategies with anti-pattern context
            strategies = reasoning_bank.search_strategies(
                task_context=f"{task_type} task failure",
                top_n=top_n * 2,  # Get more to filter
                min_win_rate=0.0  # Include all failures
            )

            # Filter for anti-patterns and format
            anti_patterns = []
            for strategy in strategies:
                # Check if it's an anti-pattern (marked in metadata)
                if strategy.task_metadata.get("is_anti_pattern"):
                    anti_patterns.append({
                        "failure_rationale": strategy.description.replace("Anti-pattern: ", ""),
                        "error_category": strategy.task_metadata.get("error_category", "unknown"),
                        "fix_applied": strategy.task_metadata.get("fix_applied"),
                        "task_description": strategy.task_metadata.get("task_description"),
                        "tools_used": list(strategy.tools_used),
                        "usage_count": strategy.usage_count,
                        "strategy_id": strategy.strategy_id
                    })

                if len(anti_patterns) >= top_n:
                    break

            return anti_patterns
        except Exception as e:
            logger.warning(f"Failed to query anti-patterns: {e}")
            return []

    def query_by_agent(self, agent_name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Query trajectories by agent name

        SECURITY FIX #4: Missing method required by Darwin + WorldModel
        Alex testing identified this gap.

        Args:
            agent_name: Name of agent to query
            limit: Maximum number of trajectories to return

        Returns:
            List of trajectory dictionaries
        """
        try:
            if hasattr(self, 'db_collection') and self.db_collection is not None:
                # MongoDB query
                results = list(self.db_collection.find(
                    {"agent_id": agent_name}
                ).sort("timestamp", DESCENDING).limit(limit))

                # Convert ObjectId to string for JSON compatibility
                for r in results:
                    if "_id" in r:
                        r["_id"] = str(r["_id"])

                return results
            else:
                # In-memory fallback
                with self._lock:
                    matching = [
                        traj for traj in self.in_memory_trajectories.values()
                        if traj.agent_id == agent_name
                    ]
                    # Sort by timestamp descending
                    matching.sort(key=lambda t: t.created_at, reverse=True)
                    # Convert to dict and limit
                    return [asdict(t) for t in matching[:limit]]

        except Exception as e:
            logger.warning(f"Failed to query by agent: {e}")
            return []

    def sample(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Sample random trajectories from buffer

        SECURITY FIX #4: Missing method required by Darwin + WorldModel
        Alex testing identified this gap.

        Args:
            limit: Maximum number of trajectories to return

        Returns:
            List of random trajectory dictionaries
        """
        try:
            if hasattr(self, 'db_collection') and self.db_collection is not None:
                # MongoDB aggregation pipeline for random sampling
                results = list(self.db_collection.aggregate([
                    {"$sample": {"size": limit}}
                ]))

                # Convert ObjectId to string
                for r in results:
                    if "_id" in r:
                        r["_id"] = str(r["_id"])

                return results
            else:
                # In-memory fallback
                with self._lock:
                    all_trajs = list(self.in_memory_trajectories.values())

                    if len(all_trajs) <= limit:
                        return [asdict(t) for t in all_trajs]

                    # Random sample
                    sampled = random.sample(all_trajs, limit)
                    return [asdict(t) for t in sampled]

        except Exception as e:
            logger.warning(f"Failed to sample trajectories: {e}")
            return []


# Thread-safe singleton pattern (like ReasoningBank)
_replay_buffer_instance: Optional[ReplayBuffer] = None
_replay_buffer_lock = threading.Lock()


def get_replay_buffer() -> ReplayBuffer:
    """
    Get or create ReplayBuffer singleton (thread-safe)

    Returns:
        Singleton ReplayBuffer instance
    """
    global _replay_buffer_instance

    if _replay_buffer_instance is None:
        with _replay_buffer_lock:
            # Double-check locking pattern
            if _replay_buffer_instance is None:
                _replay_buffer_instance = ReplayBuffer()

    return _replay_buffer_instance
