"""
Trajectory Pool - Multi-Trajectory Evolution Infrastructure
Part of SE-Darwin integration (Day 6-10)

Based on SE-Agent (arXiv 2508.02085): https://github.com/JARVIS-Xs/SE-Agent
Manages collection of evolution trajectories for cross-trajectory learning.

Key Features:
- Store rich trajectory metadata
- Automatic pruning of low performers
- Query by success/failure status
- Parent tracking for recombination
- Compression and storage optimization
"""

import json
import logging
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import hashlib

from infrastructure.security_utils import (
    sanitize_agent_name,
    validate_storage_path,
    redact_credentials
)
from infrastructure.memory.memori_client import MemoriClient
from infrastructure.memory.genesis_sql_memory import memori_enabled
from infrastructure.memory.codebook_store import get_codebook_store

try:  # Optional DreamGym integration
    from infrastructure.dreamgym.integration import DreamGymTrainer
    HAS_DREAMGYM = True
except Exception:  # pragma: no cover - DreamGym optional
    DreamGymTrainer = None  # type: ignore
    HAS_DREAMGYM = False

logger = logging.getLogger(__name__)


def _is_testing() -> bool:
    """Check if running in pytest test environment"""
    return "PYTEST_CURRENT_TEST" in os.environ


class SQLTrajectoryMirror:
    """
    Lightweight mirror that persists trajectories to Memori so SE-Darwin
    analytics can be queried from the SQL backend.
    """

    def __init__(self, agent_name: str, client: Optional[MemoriClient] = None):
        self.agent_name = agent_name
        self.client = client or MemoriClient()

    def record(self, trajectory: "Trajectory") -> None:
        try:
            payload = trajectory.to_compact_dict()
            payload["trajectory_id"] = trajectory.trajectory_id
            payload["agent_name"] = trajectory.agent_name
            payload["generation"] = trajectory.generation
            payload["status"] = trajectory.status
            self.client.upsert_trajectory(trajectory.trajectory_id, self.agent_name, payload)
        except Exception as exc:  # pragma: no cover - telemetry best effort
            logger.debug(f"Failed to mirror trajectory to SQL: {exc}")

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            return self.client.list_recent_trajectories(self.agent_name, limit)
        except Exception:
            return []


class TrajectoryStatus(Enum):
    """Status of evolution trajectory"""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    PRUNED = "pruned"


class OperatorType(Enum):
    """Type of evolution operator applied"""
    BASELINE = "baseline"  # Initial attempt, no operator
    REVISION = "revision"  # Alternative strategy from failure
    RECOMBINATION = "recombination"  # Crossover of successful elements
    REFINEMENT = "refinement"  # Optimization of promising trajectory


@dataclass
class Trajectory:
    """
    Single evolution trajectory with rich metadata

    Captures complete evolution attempt for cross-trajectory learning
    """
    # Identity
    trajectory_id: str
    generation: int
    agent_name: str

    # Lineage (for recombination tracking)
    parent_trajectories: List[str] = field(default_factory=list)
    operator_applied: Optional[str] = None  # OperatorType value

    # Execution data
    code_changes: str = ""
    problem_diagnosis: str = ""
    proposed_strategy: str = ""

    # ISSUE 6 FIX: Missing schema fields for trajectory evolution
    code_after: Optional[str] = None  # Final code after execution
    strategy_description: str = ""  # Detailed strategy explanation (aliases proposed_strategy)
    plan_id: Optional[str] = None  # Link to extracted plan (for production learning)

    # Results
    status: str = TrajectoryStatus.PENDING.value
    success_score: float = 0.0
    test_results: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)

    # Analysis
    failure_reasons: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    reasoning_pattern: str = ""
    key_insights: List[str] = field(default_factory=list)
    assumptions_made: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_time_seconds: float = 0.0
    cost_dollars: float = 0.0
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def is_successful(self, threshold: float = 0.7) -> bool:
        """Check if trajectory succeeded"""
        return self.success_score >= threshold

    def is_failed(self, threshold: float = 0.3) -> bool:
        """Check if trajectory failed"""
        return self.success_score < threshold

    def get_lineage_depth(self) -> int:
        """Get depth of trajectory lineage"""
        return len(self.parent_trajectories)

    def to_compact_dict(self) -> Dict[str, Any]:
        """
        Convert to compact dict for storage (remove large fields)

        SECURITY FIX (ISSUE #10): Redacts credentials before storage
        """
        compact = asdict(self)

        # SECURITY: Redact credentials from all text fields
        compact['code_changes'] = redact_credentials(compact.get('code_changes', ''))
        compact['problem_diagnosis'] = redact_credentials(compact.get('problem_diagnosis', ''))
        compact['proposed_strategy'] = redact_credentials(compact.get('proposed_strategy', ''))
        compact['reasoning_pattern'] = redact_credentials(compact.get('reasoning_pattern', ''))

        # Truncate large fields
        if len(compact.get('code_changes', '')) > 1000:
            compact['code_changes'] = compact['code_changes'][:1000] + "... [truncated]"
        if len(compact.get('proposed_strategy', '')) > 500:
            compact['proposed_strategy'] = compact['proposed_strategy'][:500] + "... [truncated]"

        return compact


class TrajectoryPool:
    """
    Manages collection of trajectories across generations

    Provides:
    - Trajectory storage and retrieval
    - Automatic pruning of low performers
    - Queries by success/failure status
    - Cross-trajectory analysis
    - Persistence to disk
    """

    def __init__(
        self,
        agent_name: str,
        max_trajectories: int = 50,
        success_threshold: float = 0.7,
        failure_threshold: float = 0.3,
        storage_dir: Optional[Path] = None
    ):
        """
        Initialize trajectory pool

        Args:
            agent_name: Name of agent being evolved
            max_trajectories: Maximum trajectories to keep
            success_threshold: Score threshold for success (0.7 = 70%)
            failure_threshold: Score threshold for failure (0.3 = 30%)
            storage_dir: Directory for persistence
        """
        # SECURITY FIX (ISSUE #2): Sanitize agent name to prevent path traversal
        safe_agent_name = sanitize_agent_name(agent_name)

        self.agent_name = safe_agent_name  # Store sanitized version
        self.max_trajectories = max_trajectories
        self.success_threshold = success_threshold
        self.failure_threshold = failure_threshold

        # Storage
        self.trajectories: Dict[str, Trajectory] = {}
        self.storage_dir = storage_dir or Path(f"data/trajectory_pools/{safe_agent_name}")

        # SECURITY FIX (ISSUE #2): Validate storage path is within expected directory
        # TEST FIX (October 18, 2025): Allow pytest temp directories
        base_dir = Path("data/trajectory_pools")
        base_dir.mkdir(parents=True, exist_ok=True)
        validate_storage_path(self.storage_dir, base_dir, allow_test_paths=_is_testing())

        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.total_added = 0
        self.total_pruned = 0

        self.sql_mirror = SQLTrajectoryMirror(safe_agent_name) if memori_enabled() else None
        enable_dreamgym = os.getenv("ENABLE_DREAMGYM", "true").lower() == "true"
        self.dreamgym = (
            DreamGymTrainer(agent_name=safe_agent_name)
            if enable_dreamgym and HAS_DREAMGYM
            else None
        )
        self.codebook_store = get_codebook_store()

        logger.info(
            f"TrajectoryPool initialized for {agent_name}",
            extra={
                'max_trajectories': max_trajectories,
                'success_threshold': success_threshold,
                'failure_threshold': failure_threshold
            }
        )

    def add_trajectory(self, trajectory: Trajectory) -> None:
        """
        Add trajectory to pool with automatic pruning

        Args:
            trajectory: Trajectory to add
        """
        self.trajectories[trajectory.trajectory_id] = trajectory
        self.total_added += 1

        if self.sql_mirror:
            self.sql_mirror.record(trajectory)

        if self.dreamgym:
            self.dreamgym.record_real_trajectory(trajectory)

        self._record_codebook_entry(trajectory)

        logger.debug(
            f"Added trajectory {trajectory.trajectory_id}",
            extra={
                'generation': trajectory.generation,
                'score': trajectory.success_score,
                'operator': trajectory.operator_applied
            }
        )

        # Prune if exceeding capacity
        if len(self.trajectories) > self.max_trajectories:
            pruned = self._prune_low_performers()
            logger.info(f"Pruned {pruned} low-performing trajectories")

    def get_trajectory(self, trajectory_id: str) -> Optional[Trajectory]:
        """Get specific trajectory by ID"""
        return self.trajectories.get(trajectory_id)

    def get_all_trajectories(self) -> List[Trajectory]:
        """Get all trajectories"""
        return list(self.trajectories.values())

    def size(self) -> int:
        """Get number of trajectories in pool"""
        return len(self.trajectories)

    def __len__(self) -> int:
        """Get number of trajectories in pool (Python len() support)"""
        return len(self.trajectories)

    def get_best_n(self, n: int) -> List[Trajectory]:
        """
        Get top N trajectories by success score

        Args:
            n: Number of top trajectories to return

        Returns:
            List of top N trajectories sorted by score (descending)
        """
        sorted_trajs = sorted(
            self.trajectories.values(),
            key=lambda t: t.success_score,
            reverse=True
        )
        return sorted_trajs[:n]

    def get_successful_trajectories(self) -> List[Trajectory]:
        """
        Get trajectories that succeeded

        Returns:
            List of trajectories with score >= success_threshold
        """
        return [
            t for t in self.trajectories.values()
            if t.is_successful(self.success_threshold)
        ]

    def _record_codebook_entry(self, trajectory: Trajectory) -> None:
        if not self.codebook_store:
            return
        snippet = (
            trajectory.reasoning_pattern
            or trajectory.strategy_description
            or trajectory.proposed_strategy
            or "No reasoning captured"
        )
        context = {
            "problem": trajectory.problem_diagnosis,
            "operator": trajectory.operator_applied,
            "status": trajectory.status,
        }
        try:
            self.codebook_store.record_entry(
                agent_name=self.agent_name,
                snippet=snippet,
                context=context,
                status=trajectory.status,
                score=trajectory.success_score,
            )
            trend = self.codebook_store.failure_trend(self.agent_name)
            if trend:
                logger.debug(
                    "Codebook trend %s: failure_rate=%.2f over %d entries",
                    self.agent_name,
                    trend["failure_rate"],
                    trend["window"],
                )
        except Exception as exc:  # pragma: no cover
            logger.debug(f"Failed to update codebook store: {exc}")

    def get_failed_trajectories(self) -> List[Trajectory]:
        """
        Get trajectories that failed

        Returns:
            List of trajectories with score < failure_threshold
        """
        return [
            t for t in self.trajectories.values()
            if t.is_failed(self.failure_threshold)
        ]

    def get_by_generation(self, generation: int) -> List[Trajectory]:
        """Get all trajectories from specific generation"""
        return [
            t for t in self.trajectories.values()
            if t.generation == generation
        ]

    def get_by_operator(self, operator: OperatorType) -> List[Trajectory]:
        """Get all trajectories created by specific operator"""
        return [
            t for t in self.trajectories.values()
            if t.operator_applied == operator.value
        ]

    def get_diverse_successful_pairs(self, n: int = 5) -> List[Tuple[Trajectory, Trajectory]]:
        """
        Get N diverse pairs of successful trajectories for recombination

        Selects pairs that used different reasoning patterns for maximum diversity

        Args:
            n: Number of pairs to return

        Returns:
            List of (trajectory_a, trajectory_b) tuples
        """
        successful = self.get_successful_trajectories()

        if len(successful) < 2:
            return []

        pairs = []
        used_ids = set()

        for i in range(len(successful)):
            for j in range(i + 1, len(successful)):
                traj_a = successful[i]
                traj_b = successful[j]

                # Skip if either already used
                if traj_a.trajectory_id in used_ids or traj_b.trajectory_id in used_ids:
                    continue

                # Prefer pairs with different reasoning patterns
                diversity_score = 0
                if traj_a.reasoning_pattern != traj_b.reasoning_pattern:
                    diversity_score += 1
                if set(traj_a.tools_used) != set(traj_b.tools_used):
                    diversity_score += 1

                if diversity_score > 0:
                    pairs.append((traj_a, traj_b))
                    used_ids.add(traj_a.trajectory_id)
                    used_ids.add(traj_b.trajectory_id)

                if len(pairs) >= n:
                    break

            if len(pairs) >= n:
                break

        return pairs[:n]

    def get_pool_insights(self, max_insights: int = 10) -> List[str]:
        """
        Extract key insights from all trajectories for refinement

        Args:
            max_insights: Maximum number of insights to return

        Returns:
            List of insight strings
        """
        all_insights = []

        for traj in self.get_successful_trajectories():
            all_insights.extend(traj.key_insights)

        # Deduplicate and prioritize
        unique_insights = list(dict.fromkeys(all_insights))  # Preserve order
        return unique_insights[:max_insights]

    def get_common_failure_patterns(self) -> List[str]:
        """
        Identify common failure patterns across failed trajectories

        Returns:
            List of common failure reasons
        """
        failure_counts: Dict[str, int] = {}

        for traj in self.get_failed_trajectories():
            for reason in traj.failure_reasons:
                failure_counts[reason] = failure_counts.get(reason, 0) + 1

        # Sort by frequency
        sorted_failures = sorted(
            failure_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [reason for reason, count in sorted_failures if count >= 2]

    def sample_dreamgym_batch(
        self,
        task_signature: str,
        batch_size: int = 32,
    ) -> List[Dict[str, Any]]:
        """
        Generate synthetic experiences via DreamGym if enabled.
        """
        if not self.dreamgym:
            return []
        return self.dreamgym.generate_synthetic_batch(task_signature, batch_size)

    def _prune_low_performers(self) -> int:
        """
        Prune lowest-scoring trajectories to maintain capacity

        Keeps:
        - All successful trajectories (score >= success_threshold)
        - Recent trajectories (last 10 generations)
        - Diverse operator types

        Returns:
            Number of trajectories pruned
        """
        if len(self.trajectories) <= self.max_trajectories:
            return 0

        # Get current generation
        max_generation = max(
            (t.generation for t in self.trajectories.values()),
            default=0
        )

        # Candidates for pruning (low score, old generation)
        prunable = []
        must_keep = []

        for traj in self.trajectories.values():
            # Always keep successful trajectories
            if traj.is_successful(self.success_threshold):
                must_keep.append(traj)
            # Always keep recent trajectories (last 10 generations)
            elif traj.generation >= max_generation - 10:
                must_keep.append(traj)
            else:
                prunable.append(traj)

        # Sort prunable by score (ascending)
        prunable.sort(key=lambda t: t.success_score)

        # Calculate how many to prune
        target_size = self.max_trajectories
        current_size = len(self.trajectories)
        must_keep_count = len(must_keep)

        num_to_prune = max(0, current_size - target_size)
        num_can_prune = len(prunable)

        actual_prune_count = min(num_to_prune, num_can_prune)

        # Prune lowest performers
        for i in range(actual_prune_count):
            traj = prunable[i]
            traj.status = TrajectoryStatus.PRUNED.value
            del self.trajectories[traj.trajectory_id]
            self.total_pruned += 1

        return actual_prune_count

    def attach_workspace(self, task_id: str) -> 'IterResearchWorkspace':
        """Attach an IterResearch workspace to this trajectory pool."""
        from infrastructure.iterresearch_workspace import IterResearchWorkspace
        self.workspace = IterResearchWorkspace(task_id=task_id)
        return self.workspace

    async def add_trajectory_with_workspace(
        self,
        trajectory: Trajectory,
        workspace_snapshot: Optional[Dict] = None
    ) -> None:
        """Add trajectory and optionally save workspace snapshot."""
        self.add_trajectory(trajectory)

        if hasattr(self, 'workspace') and workspace_snapshot:
            # Store workspace snapshot in trajectory metadata
            if not hasattr(trajectory, 'metadata') or trajectory.metadata is None:
                trajectory.metadata = {}
            trajectory.metadata["workspace_snapshot"] = workspace_snapshot

    def get_workspace_history(self, task_id: str) -> List[Dict]:
        """Get workspace evolution for a specific task."""
        workspaces = []
        for trajectory in self.trajectories.values():
            if (hasattr(trajectory, 'metadata') and trajectory.metadata and
                "workspace_snapshot" in trajectory.metadata):
                ws = trajectory.metadata.get("workspace_snapshot")
                if ws and ws.get("task_id") == task_id:
                    workspaces.append(ws)
        return workspaces

    def save_to_disk(self) -> Path:
        """
        Persist trajectory pool to disk

        Returns:
            Path to saved file
        """
        save_path = self.storage_dir / "trajectory_pool.json"

        pool_data = {
            'agent_name': self.agent_name,
            'max_trajectories': self.max_trajectories,
            'success_threshold': self.success_threshold,
            'failure_threshold': self.failure_threshold,
            'total_added': self.total_added,
            'total_pruned': self.total_pruned,
            'trajectories': {
                tid: traj.to_compact_dict()
                for tid, traj in self.trajectories.items()
            },
            'saved_at': datetime.now(timezone.utc).isoformat()
        }

        with open(save_path, 'w') as f:
            json.dump(pool_data, f, indent=2)

        logger.info(f"Saved trajectory pool to {save_path}")
        return save_path

    @classmethod
    def load_from_disk(cls, agent_name: str, storage_dir: Optional[Path] = None) -> 'TrajectoryPool':
        """
        Load trajectory pool from disk

        Args:
            agent_name: Name of agent
            storage_dir: Directory where pool is stored

        Returns:
            Loaded TrajectoryPool instance
        """
        # SECURITY FIX (ISSUE #2): Sanitize agent name
        safe_agent_name = sanitize_agent_name(agent_name)

        if storage_dir is None:
            storage_dir = Path(f"data/trajectory_pools/{safe_agent_name}")

        # SECURITY FIX (ISSUE #2): Validate storage path
        # TEST FIX (October 18, 2025): Allow pytest temp directories
        base_dir = Path("data/trajectory_pools")
        validate_storage_path(storage_dir, base_dir, allow_test_paths=_is_testing())

        load_path = storage_dir / "trajectory_pool.json"

        if not load_path.exists():
            logger.warning(f"No saved pool found at {load_path}, creating new pool")
            return cls(agent_name=agent_name, storage_dir=storage_dir)

        with open(load_path, 'r') as f:
            pool_data = json.load(f)

        # Create pool
        pool = cls(
            agent_name=pool_data['agent_name'],
            max_trajectories=pool_data['max_trajectories'],
            success_threshold=pool_data['success_threshold'],
            failure_threshold=pool_data['failure_threshold'],
            storage_dir=storage_dir
        )

        # Restore trajectories
        for tid, traj_data in pool_data['trajectories'].items():
            traj = Trajectory(**traj_data)
            pool.trajectories[tid] = traj

        pool.total_added = pool_data['total_added']
        pool.total_pruned = pool_data['total_pruned']

        logger.info(f"Loaded trajectory pool from {load_path} ({len(pool.trajectories)} trajectories)")
        return pool

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get pool statistics

        Returns:
            Dictionary of statistics
        """
        if not self.trajectories:
            return {
                'total_trajectories': 0,
                'successful_count': 0,
                'failed_count': 0,
                'average_score': 0.0,
                'best_score': 0.0,
                'total_added': self.total_added,
                'total_pruned': self.total_pruned
            }

        scores = [t.success_score for t in self.trajectories.values()]

        return {
            'total_trajectories': len(self.trajectories),
            'successful_count': len(self.get_successful_trajectories()),
            'failed_count': len(self.get_failed_trajectories()),
            'average_score': sum(scores) / len(scores),
            'best_score': max(scores),
            'worst_score': min(scores),
            'total_added': self.total_added,
            'total_pruned': self.total_pruned,
            'operator_distribution': self._get_operator_distribution(),
            'generation_distribution': self._get_generation_distribution()
        }

    def _get_operator_distribution(self) -> Dict[str, int]:
        """Get count of trajectories by operator type"""
        distribution: Dict[str, int] = {}
        for traj in self.trajectories.values():
            op = traj.operator_applied or 'none'
            distribution[op] = distribution.get(op, 0) + 1
        return distribution

    def _get_generation_distribution(self) -> Dict[int, int]:
        """Get count of trajectories by generation"""
        distribution: Dict[int, int] = {}
        for traj in self.trajectories.values():
            gen = traj.generation
            distribution[gen] = distribution.get(gen, 0) + 1
        return distribution


def get_trajectory_pool(
    agent_name: str,
    max_trajectories: int = 50,
    load_existing: bool = True
) -> TrajectoryPool:
    """
    Factory function to get or create trajectory pool

    Args:
        agent_name: Name of agent
        max_trajectories: Maximum trajectories to keep
        load_existing: Whether to load from disk if exists

    Returns:
        TrajectoryPool instance
    """
    if load_existing:
        return TrajectoryPool.load_from_disk(agent_name)
    else:
        return TrajectoryPool(agent_name=agent_name, max_trajectories=max_trajectories)
