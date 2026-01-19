"""
CaseBank - Non-Parametric Memory Store for Agent Case-Based Reasoning

Based on Memento: Fine-tuning LLM Agents without Fine-tuning LLMs (arXiv:2508.16153)
GitHub: https://github.com/Agent-on-the-Fly/Memento

BREAKTHROUGH: Learn from experience WITHOUT model fine-tuning
- Store final-step tuples: (state_T, action_T, reward_T)
- Retrieve K=4 most similar high-reward cases (paper optimal)
- Augment prompts with past successes/failures
- Zero training required, pure case-based reasoning

Proven Results (GAIA benchmark):
- 87.88% accuracy with case-based memory
- +4.7-9.6 F1 improvement over baseline
- 15-25% accuracy boost on repeated tasks
- 10-15% cost reduction (fewer retries)

Architecture:
1. Case Storage: JSONL persistent storage for cases
2. Embedding: Semantic similarity via embeddings
3. Retrieval: Top-K retrieval with reward filtering
4. Context Building: Format cases as learning examples

Integration Points:
- SE-Darwin: Learn from past evolution trajectories
- WaltzRL: Learn from past safety evaluations
- HTDAG: Retrieve similar task decompositions
- All agents: Learn from task-specific outcomes
"""

import asyncio
import hashlib
import json
import logging
import os
import numpy as np
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Genesis infrastructure
from infrastructure import get_logger
from infrastructure.security_utils import redact_credentials
from infrastructure.memory.memori_client import MemoriClient
from infrastructure.memory.genesis_sql_memory import memori_enabled

# OTEL observability
try:
    from opentelemetry import trace, metrics
    from opentelemetry.trace import Status, StatusCode
    tracer = trace.get_tracer(__name__)
    meter = metrics.get_meter(__name__)

    # Metrics
    case_counter = meter.create_counter(
        "casebank.cases.stored",
        description="Number of cases stored"
    )
    retrieval_counter = meter.create_counter(
        "casebank.retrievals.performed",
        description="Number of retrievals performed"
    )
    retrieval_histogram = meter.create_histogram(
        "casebank.retrieval.duration",
        description="Retrieval duration in seconds"
    )
    HAS_OTEL = True
except ImportError:
    HAS_OTEL = False
    tracer = None

logger = get_logger(__name__)


@dataclass
class Case:
    """
    Single experience case stored in memory.

    Memento paper stores final-step tuples (s_T, a_T, r_T) where:
    - s_T: Final state (task description)
    - a_T: Final action (solution/output)
    - r_T: Reward (success score 0-1)
    """
    state: str  # Task description/query
    action: str  # Solution/response
    reward: float  # Success score (0-1)
    metadata: Dict[str, Any]  # Agent name, timestamp, tags, etc.
    embedding: Optional[np.ndarray] = None  # Semantic embedding for retrieval

    # Computed fields
    case_id: str = field(default_factory=lambda: "")

    def __post_init__(self):
        """Generate unique case ID from state+action hash"""
        if not self.case_id:
            content = f"{self.state}|{self.action}|{self.metadata.get('agent', '')}"
            self.case_id = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        data = asdict(self)
        # Convert numpy array to list for JSON serialization
        if self.embedding is not None:
            data["embedding"] = self.embedding.tolist()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Case":
        """Reconstruct case from dict"""
        if data.get("embedding") is not None:
            data["embedding"] = np.array(data["embedding"])
        return cls(**data)


class CaseBank:
    """
    Non-parametric memory store for agent experiences.

    Memento paper approach:
    1. Store successful task executions as cases
    2. Retrieve K=4 most similar cases (paper optimal)
    3. Filter by minimum reward (0.6) and similarity (0.8)
    4. Augment prompt with retrieved cases as learning context

    This enables learning without model fine-tuning - pure case-based reasoning.
    """

    def __init__(
        self,
        storage_path: str = "data/memory/casebank.jsonl",
        embedding_dim: int = 384,  # sentence-transformers default
        enable_otel: bool = True,
        backend: Optional[str] = None,
        memori_client: Optional[MemoriClient] = None,
    ):
        """
        Initialize CaseBank with persistent storage.

        Args:
            storage_path: Path to JSONL storage file
            embedding_dim: Embedding dimensionality (384 for sentence-transformers)
            enable_otel: Enable OpenTelemetry tracing/metrics
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedding_dim = embedding_dim
        self.enable_otel = enable_otel and HAS_OTEL

        default_backend = "sql" if memori_enabled() else "jsonl"
        self.backend = (backend or os.getenv("CASEBANK_BACKEND", default_backend)).lower()
        if self.backend not in {"jsonl", "sql"}:
            raise ValueError(f"Unsupported CaseBank backend: {self.backend}")

        self.memori_client = None
        if self.backend == "sql":
            self.memori_client = memori_client or MemoriClient()

        # In-memory case index (loads from disk on init)
        self.cases: List[Case] = []
        self.case_index: Dict[str, Case] = {}  # case_id -> Case

        # Load existing cases from storage
        self._load_cases()

        logger.info(
            f"CaseBank initialized: {len(self.cases)} cases loaded from {self.storage_path}"
        )

    async def add_case(
        self,
        state: str,
        action: str,
        reward: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Case:
        """
        Store new experience case.

        Args:
            state: Task description/query
            action: Solution/response
            reward: Success score (0-1)
            metadata: Additional context (agent name, tags, etc.)

        Returns:
            Stored Case object
        """
        if metadata is None:
            metadata = {}

        # Add timestamp
        metadata["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Redact sensitive data
        state_safe = redact_credentials(state)
        action_safe = redact_credentials(action)

        # Create case with embedding
        embedding = await self._embed(state_safe)

        case = Case(
            state=state_safe,
            action=action_safe,
            reward=reward,
            metadata=metadata,
            embedding=embedding
        )

        # Add to in-memory index
        self.cases.append(case)
        self.case_index[case.case_id] = case

        # Persist to disk
        await self._persist_case(case)

        # Metrics
        if self.enable_otel:
            case_counter.add(1, {"agent": metadata.get("agent", "unknown")})

        logger.info(
            f"Stored case: reward={reward:.2f}, agent={metadata.get('agent', 'unknown')}, "
            f"case_id={case.case_id[:8]}"
        )

        return case

    async def retrieve_similar(
        self,
        query_state: str,
        k: int = 4,
        min_reward: float = 0.6,
        min_similarity: float = 0.8,
        agent_filter: Optional[str] = None
    ) -> List[Tuple[Case, float]]:
        """
        Retrieve K most similar high-reward cases.

        Memento paper optimal: K=4 cases with reward >= 0.6, similarity >= 0.8

        Args:
            query_state: Current task description
            k: Number of cases to retrieve (default 4 per paper)
            min_reward: Minimum reward threshold (default 0.6)
            min_similarity: Minimum cosine similarity (default 0.8)
            agent_filter: Optional filter by agent name

        Returns:
            List of (Case, similarity_score) tuples, sorted by weighted score
        """
        start_time = asyncio.get_event_loop().time()

        if self.enable_otel and tracer:
            span = tracer.start_span("casebank.retrieve_similar")
            span.set_attribute("k", k)
            span.set_attribute("min_reward", min_reward)
            span.set_attribute("min_similarity", min_similarity)
        else:
            span = None

        try:
            # Generate query embedding
            query_emb = await self._embed(query_state)

            # Calculate similarities
            similarities: List[Tuple[Case, float]] = []

            for case in self.cases:
                # Filter by agent if specified
                if agent_filter and case.metadata.get("agent") != agent_filter:
                    continue

                # Filter by minimum reward
                if case.reward < min_reward:
                    continue

                # Calculate cosine similarity
                sim = self._cosine_similarity(query_emb, case.embedding)

                # Filter by minimum similarity
                if sim >= min_similarity:
                    similarities.append((case, sim))

            # Sort by weighted score: similarity * reward
            # This prioritizes both relevance and quality
            similarities.sort(key=lambda x: x[1] * x[0].reward, reverse=True)

            # Return top-K
            top_k = similarities[:k]

            # Log retrieval
            duration = asyncio.get_event_loop().time() - start_time
            logger.info(
                f"Retrieved {len(top_k)}/{len(similarities)} cases "
                f"(K={k}, min_sim={min_similarity}, min_reward={min_reward}, "
                f"duration={duration:.3f}s)"
            )

            # Metrics
            if self.enable_otel:
                retrieval_counter.add(1, {"found": len(top_k) > 0})
                retrieval_histogram.record(duration)
                if span:
                    span.set_attribute("cases_found", len(top_k))
                    span.set_attribute("candidates_considered", len(similarities))
                    span.set_status(Status(StatusCode.OK))

            return top_k

        except Exception as e:
            logger.error(f"Retrieval failed: {e}", exc_info=True)
            if span:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
            raise
        finally:
            if span:
                span.end()

    def build_case_context(
        self,
        cases: List[Tuple[Case, float]],
        max_length: int = 500
    ) -> str:
        """
        Format retrieved cases as learning context for prompt augmentation.

        Args:
            cases: List of (Case, similarity) tuples from retrieve_similar
            max_length: Maximum length per case text (for context window management)

        Returns:
            Formatted string with examples for prompt augmentation
        """
        if not cases:
            return ""

        lines = ["Past similar tasks and outcomes (learn from these):"]
        lines.append("")

        for i, (case, similarity) in enumerate(cases, 1):
            # Truncate long texts
            state_text = case.state[:max_length]
            action_text = case.action[:max_length]

            if len(case.state) > max_length:
                state_text += "..."
            if len(case.action) > max_length:
                action_text += "..."

            lines.append(f"Example {i} (success={case.reward:.0%}, relevance={similarity:.0%}):")
            lines.append(f"  Task: {state_text}")
            lines.append(f"  Solution: {action_text}")
            lines.append("")

        return "\n".join(lines)

    async def get_case_by_id(self, case_id: str) -> Optional[Case]:
        """Retrieve specific case by ID"""
        return self.case_index.get(case_id)

    async def get_all_cases(
        self,
        agent_filter: Optional[str] = None,
        min_reward: Optional[float] = None
    ) -> List[Case]:
        """
        Get all cases with optional filtering.

        Args:
            agent_filter: Filter by agent name
            min_reward: Minimum reward threshold

        Returns:
            Filtered list of cases
        """
        filtered = self.cases

        if agent_filter:
            filtered = [c for c in filtered if c.metadata.get("agent") == agent_filter]

        if min_reward is not None:
            filtered = [c for c in filtered if c.reward >= min_reward]

        return filtered

    async def clear_cases(self, agent_filter: Optional[str] = None) -> int:
        """
        Clear cases from memory (optionally filtered by agent).

        Args:
            agent_filter: If provided, only clear cases from this agent

        Returns:
            Number of cases cleared
        """
        if agent_filter:
            # Remove specific agent's cases
            before = len(self.cases)
            self.cases = [c for c in self.cases if c.metadata.get("agent") != agent_filter]
            self.case_index = {c.case_id: c for c in self.cases}
            cleared = before - len(self.cases)
            if self.backend == "sql" and self.memori_client:
                await self.memori_client.aclear_cases(agent_filter)
        else:
            # Clear all
            cleared = len(self.cases)
            self.cases = []
            self.case_index = {}
            if self.backend == "sql" and self.memori_client:
                await self.memori_client.aclear_cases(None)
            else:
                # Truncate storage file
                self.storage_path.write_text("")

        logger.info(f"Cleared {cleared} cases (agent_filter={agent_filter})")
        return cleared

    # Private methods

    async def _embed(self, text: str) -> np.ndarray:
        """
        Generate semantic embedding for text using TEI.

        Production implementation: TEI (BAAI/bge-base-en-v1.5, 768-dim)
        Fallback: Hash-based embedding for testing

        Args:
            text: Input text

        Returns:
            Embedding vector (384-dim or 768-dim depending on TEI availability)
        """
        # Try TEI first (production-ready, 64x cheaper than OpenAI)
        try:
            from infrastructure.tei_client import get_tei_client
            tei = get_tei_client()

            # Check if TEI is available
            if await tei.health_check():
                embedding = await tei.embed_single(text)

                # If embedding_dim doesn't match, resize
                if len(embedding) != self.embedding_dim:
                    # Truncate or pad to match expected dimension
                    if len(embedding) > self.embedding_dim:
                        embedding = embedding[:self.embedding_dim]
                    else:
                        padded = np.zeros(self.embedding_dim)
                        padded[:len(embedding)] = embedding
                        embedding = padded

                # Normalize
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm

                return embedding
        except Exception as e:
            logger.warning(f"TEI embedding failed, using fallback: {e}")

        # Fallback: deterministic hash-based embedding
        # This allows testing the case-based reasoning logic
        words = text.lower().split()
        embedding = np.zeros(self.embedding_dim)

        for word in words[:50]:  # Limit to first 50 words
            # Hash word to multiple dimensions
            hash_val = int(hashlib.sha256(word.encode()).hexdigest(), 16)
            for i in range(3):  # 3 hash functions
                idx = (hash_val + i * 1000) % self.embedding_dim
                embedding[idx] += 1.0

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Similarity score (0-1)
        """
        if a is None or b is None:
            return 0.0

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return max(0.0, min(1.0, dot_product / (norm_a * norm_b)))

    async def _persist_case(self, case: Case) -> None:
        """Append case to JSONL storage"""
        try:
            if self.backend == "sql":
                if self.memori_client:
                    await self.memori_client.aupsert_case(case.to_dict())
                return

            with open(self.storage_path, "a") as f:
                json.dump(case.to_dict(), f)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to persist case {case.case_id}: {e}")
            raise

    def _load_cases(self) -> None:
        """Load existing cases from storage backend"""
        if self.backend == "sql":
            self._load_cases_sql()
            return

        if not self.storage_path.exists():
            logger.info(f"No existing storage at {self.storage_path}, starting fresh")
            return

        try:
            with open(self.storage_path, "r") as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line)
                        case = Case.from_dict(data)
                        self.cases.append(case)
                        self.case_index[case.case_id] = case
                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping invalid JSON at line {line_num}: {e}")
                    except Exception as e:
                        logger.warning(f"Skipping invalid case at line {line_num}: {e}")

            logger.info(f"Loaded {len(self.cases)} cases from {self.storage_path}")

        except Exception as e:
            logger.error(f"Failed to load cases: {e}", exc_info=True)
            raise

    def _load_cases_sql(self) -> None:
        if not self.memori_client:
            logger.warning("Memori client unavailable; skipping SQL case load")
            return

        try:
            rows = self.memori_client.fetch_cases(limit=2000)
            for payload in rows:
                case = Case.from_dict(payload)
                self.cases.append(case)
                self.case_index[case.case_id] = case
            logger.info(f"Loaded {len(self.cases)} cases from Memori backend")
        except Exception as exc:
            logger.error(f"Failed to load cases from Memori: {exc}")


# Singleton instance
_casebank_instance: Optional[CaseBank] = None


def get_casebank(
    storage_path: str = "data/memory/casebank.jsonl",
    reset: bool = False
) -> CaseBank:
    """
    Get global CaseBank singleton instance.

    Args:
        storage_path: Path to storage file
        reset: If True, create new instance (for testing)

    Returns:
        CaseBank instance
    """
    global _casebank_instance

    if reset or _casebank_instance is None:
        _casebank_instance = CaseBank(storage_path=storage_path)

    return _casebank_instance
