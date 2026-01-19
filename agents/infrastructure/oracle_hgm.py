"""
Oracle HGM - Hypothesis-Guided Multi-Agent Tree Search for Genesis
Integrates HGM tree search with CMP-based candidate selection

Based on:
- HGM (arXiv:2510.21614): Huxley-Gödel Machine with optimistic tree search
- Darwin Gödel Machine (arXiv:2505.22954): Self-improving code evolution
- Agent-as-a-Judge: CMP scoring for candidate selection

Key Features:
- Tree-based search space exploration (HGM approach)
- CMP-based candidate selection (coherent multi-perspective scoring)
- Efficient candidate generation via LLM-guided hypotheses
- Integration with Genesis evolution operators
- Production-ready with OTEL observability

Architecture:
1. Propose N candidate edits using LLM-guided hypotheses
2. Score each candidate using CMP metric (judge.py)
3. Select top-K by CMP score (coherence across perspectives)
4. Expand promising nodes in tree
5. Archive best solutions to TrajectoryPool
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
import numpy as np

# Genesis infrastructure
from infrastructure import get_logger
from infrastructure.llm_client import LLMClient, LLMFactory, LLMProvider
from infrastructure.judge import AgentJudge, JudgeScore, CMPScore, get_agent_judge
from infrastructure.trajectory_pool import (
    Trajectory,
    TrajectoryPool,
    TrajectoryStatus,
    get_trajectory_pool
)

# OTEL observability
try:
    from opentelemetry import trace
    tracer = trace.get_tracer(__name__)
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    tracer = None

logger = get_logger(__name__)


class EditStrategy(str, Enum):
    """Strategies for generating candidate edits"""
    HYPOTHESIS_GUIDED = "hypothesis_guided"  # LLM generates hypotheses for improvement
    OPERATOR_BASED = "operator_based"  # Apply evolution operators
    RANDOM_MUTATION = "random_mutation"  # Random code mutations
    HYBRID = "hybrid"  # Combination of strategies


@dataclass
class CandidateEdit:
    """
    A candidate code edit proposal

    Attributes:
        code: Modified code
        hypothesis: Hypothesis that motivated this edit
        strategy: How this candidate was generated
        parent_id: ID of parent node in tree
        edit_id: Unique identifier for this edit
        metadata: Additional context
    """
    code: str
    hypothesis: str
    strategy: EditStrategy
    parent_id: Optional[str] = None
    edit_id: str = field(default_factory=lambda: hashlib.sha256(
        f"{time.time()}".encode()
    ).hexdigest()[:16])
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "code": self.code,
            "hypothesis": self.hypothesis,
            "strategy": self.strategy.value,
            "parent_id": self.parent_id,
            "edit_id": self.edit_id,
            "metadata": self.metadata
        }


@dataclass
class TreeNode:
    """
    Node in HGM tree search

    Each node represents a code version with:
    - Code content
    - CMP score (if evaluated)
    - Children (derived versions)
    - Parent (source version)
    """
    node_id: str
    code: str
    hypothesis: str
    cmp_score: Optional[CMPScore] = None
    judge_scores: List[JudgeScore] = field(default_factory=list)
    children: List['TreeNode'] = field(default_factory=list)
    parent_id: Optional[str] = None
    visit_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def mean_score(self) -> float:
        """Get mean CMP score"""
        if self.cmp_score:
            return self.cmp_score.cmp_score
        return 0.0

    @property
    def is_leaf(self) -> bool:
        """Check if this is a leaf node"""
        return len(self.children) == 0

    def add_child(self, child: 'TreeNode') -> None:
        """Add child node"""
        self.children.append(child)
        child.parent_id = self.node_id


class OracleHGM:
    """
    Oracle HGM - Hypothesis-Guided Multi-Agent tree search

    Implements HGM paper's tree search with CMP-based selection:
    1. Generate candidate edits (N proposals)
    2. Score with CMP metric (coherent multi-perspective)
    3. Select top-K best candidates
    4. Expand tree by evaluating children
    5. Iterate until convergence

    Key Innovation: CMP scoring replaces utility measures for better code quality.
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        judge: Optional[AgentJudge] = None,
        trajectory_pool: Optional[TrajectoryPool] = None,
        n_proposals: int = 10,
        top_k: int = 3,
        max_depth: int = 5,
        cmp_threshold: float = 70.0
    ):
        """
        Initialize Oracle HGM

        Args:
            llm_client: LLM for generating hypotheses
            judge: Agent-as-a-Judge for scoring
            trajectory_pool: Pool for archiving best solutions
            n_proposals: Number of candidates to propose per iteration
            top_k: Number of top candidates to expand
            max_depth: Maximum tree depth
            cmp_threshold: Minimum CMP score to archive
        """
        # Get LLM client (create if not provided)
        if llm_client is None:
            try:
                from anthropic import Anthropic
                import os
                llm_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            except Exception as e:
                logger.warning(f"Could not initialize LLM client: {e}")
                llm_client = None

        self.llm_client = llm_client
        # Get judge (create if not provided)
        if judge is None:
            try:
                from infrastructure.judge import AgentJudge
                judge = AgentJudge()
            except Exception as e:
                logger.warning(f"Could not initialize AgentJudge: {e}")
                judge = None
        self.judge = judge
        # Trajectory pool - initialized on-demand if not provided
        if trajectory_pool is None:
            from infrastructure.trajectory_pool import TrajectoryPool
            self.trajectory_pool = TrajectoryPool(agent_name="oracle_hgm")
        else:
            self.trajectory_pool = trajectory_pool
        self.n_proposals = n_proposals
        self.top_k = top_k
        self.max_depth = max_depth
        self.cmp_threshold = cmp_threshold

        # Tree state
        self.nodes: Dict[str, TreeNode] = {}
        self.root: Optional[TreeNode] = None

        logger.info(
            f"OracleHGM initialized: n_proposals={n_proposals}, "
            f"top_k={top_k}, max_depth={max_depth}, "
            f"cmp_threshold={cmp_threshold}"
        )

    async def propose_edits(
        self,
        code: str,
        task: str,
        parent_id: Optional[str] = None,
        n: Optional[int] = None,
        strategy: EditStrategy = EditStrategy.HYPOTHESIS_GUIDED
    ) -> List[CandidateEdit]:
        """
        Propose N candidate edits for given code

        Args:
            code: Current code version
            task: Task description/requirements
            parent_id: Parent node ID in tree
            n: Number of proposals (default: self.n_proposals)
            strategy: Edit generation strategy

        Returns:
            List of CandidateEdit proposals
        """
        n = n or self.n_proposals

        span_name = "oracle_hgm.propose_edits" if OTEL_AVAILABLE else None
        if OTEL_AVAILABLE and tracer:
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("hgm.n_proposals", n)
                span.set_attribute("hgm.strategy", strategy.value)
                return await self._propose_edits_impl(code, task, parent_id, n, strategy)
        else:
            return await self._propose_edits_impl(code, task, parent_id, n, strategy)

    async def _propose_edits_impl(
        self,
        code: str,
        task: str,
        parent_id: Optional[str],
        n: int,
        strategy: EditStrategy
    ) -> List[CandidateEdit]:
        """Internal implementation of propose_edits"""
        if strategy == EditStrategy.HYPOTHESIS_GUIDED:
            return await self._generate_hypothesis_guided(code, task, parent_id, n)
        elif strategy == EditStrategy.OPERATOR_BASED:
            return await self._generate_operator_based(code, task, parent_id, n)
        elif strategy == EditStrategy.HYBRID:
            # Mix of hypothesis-guided and operator-based
            n_hyp = n // 2
            n_op = n - n_hyp
            hyp_edits = await self._generate_hypothesis_guided(code, task, parent_id, n_hyp)
            op_edits = await self._generate_operator_based(code, task, parent_id, n_op)
            return hyp_edits + op_edits
        else:
            raise ValueError(f"Unsupported strategy: {strategy}")

    async def _generate_hypothesis_guided(
        self,
        code: str,
        task: str,
        parent_id: Optional[str],
        n: int
    ) -> List[CandidateEdit]:
        """Generate candidate edits using hypothesis-guided approach"""
        prompt = f"""You are an expert AI researcher improving agent code.

CURRENT CODE:
```python
{code}
```

TASK DESCRIPTION:
{task}

INSTRUCTIONS:
Generate {n} diverse hypotheses for improving this code. For each hypothesis:
1. Identify a specific weakness or improvement opportunity
2. Propose a concrete code modification
3. Explain why this would improve the code

Focus on:
- Correctness improvements (fix bugs, edge cases)
- Completeness improvements (add missing features)
- Efficiency improvements (optimize performance)
- Safety improvements (error handling, security)

Respond in JSON format:
{{
    "hypotheses": [
        {{
            "hypothesis": "<specific improvement idea>",
            "modified_code": "<improved code>",
            "reasoning": "<why this helps>"
        }},
        ...
    ]
}}

Make each hypothesis substantially different from the others."""

        try:
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o",
                temperature=0.8,  # Higher temperature for diversity
                response_format={"type": "json_object"}
            )

            result = json.loads(response)
            hypotheses = result.get("hypotheses", [])

            candidates = []
            for hyp in hypotheses[:n]:
                candidate = CandidateEdit(
                    code=hyp.get("modified_code", code),
                    hypothesis=hyp.get("hypothesis", "Unspecified improvement"),
                    strategy=EditStrategy.HYPOTHESIS_GUIDED,
                    parent_id=parent_id,
                    metadata={"reasoning": hyp.get("reasoning", "")}
                )
                candidates.append(candidate)

            logger.info(f"Generated {len(candidates)} hypothesis-guided candidates")
            return candidates

        except Exception as e:
            logger.error(f"Failed to generate hypotheses: {e}", exc_info=True)
            # Return original code as fallback
            return [CandidateEdit(
                code=code,
                hypothesis="Fallback: original code",
                strategy=EditStrategy.HYPOTHESIS_GUIDED,
                parent_id=parent_id,
                metadata={"error": str(e)}
            )]

    async def _generate_operator_based(
        self,
        code: str,
        task: str,
        parent_id: Optional[str],
        n: int
    ) -> List[CandidateEdit]:
        """Generate candidate edits using evolution operators"""
        # Placeholder: Integrate with existing SE operators
        # In full implementation, would use RevisionOperator, RecombinationOperator, etc.
        logger.info(f"Operator-based generation not yet implemented, using hypothesis-guided")
        return await self._generate_hypothesis_guided(code, task, parent_id, n)

    async def cmp_score(
        self,
        candidates: List[CandidateEdit],
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[CandidateEdit, CMPScore]]:
        """
        Score candidates using CMP metric

        Args:
            candidates: List of candidate edits to score
            task: Task description for evaluation criteria
            context: Additional evaluation context

        Returns:
            List of (candidate, cmp_score) tuples sorted by CMP score descending
        """
        context = context or {}

        # Score each candidate
        scored_candidates = []
        for candidate in candidates:
            # Get judge score for this candidate
            judge_score = await self.judge.score_output(
                output=candidate.code,
                criteria=task,
                context={
                    **context,
                    "hypothesis": candidate.hypothesis,
                    "strategy": candidate.strategy.value
                }
            )

            # Calculate CMP score (single judge, so coherence penalty is 0)
            cmp_score = self.judge.calculate_cmp_score([judge_score])

            scored_candidates.append((candidate, cmp_score))

            logger.debug(
                f"Candidate {candidate.edit_id[:8]}: "
                f"CMP={cmp_score.cmp_score:.1f}, "
                f"hypothesis='{candidate.hypothesis[:50]}...'"
            )

        # Sort by CMP score descending
        scored_candidates.sort(key=lambda x: x[1].cmp_score, reverse=True)

        return scored_candidates

    async def select_best(
        self,
        candidates: List[Tuple[CandidateEdit, CMPScore]],
        k: Optional[int] = None
    ) -> List[Tuple[CandidateEdit, CMPScore]]:
        """
        Select top-K candidates by CMP score

        Args:
            candidates: List of (candidate, cmp_score) tuples
            k: Number to select (default: self.top_k)

        Returns:
            Top-K candidates by CMP score
        """
        k = k or self.top_k
        selected = candidates[:k]

        logger.info(
            f"Selected top-{k} candidates with CMP scores: "
            f"{[f'{s[1].cmp_score:.1f}' for s in selected]}"
        )

        return selected

    async def expand_tree(
        self,
        node: TreeNode,
        task: str,
        depth: int = 0
    ) -> List[TreeNode]:
        """
        Expand tree from given node by generating and evaluating children

        Args:
            node: Node to expand from
            task: Task description
            depth: Current depth in tree

        Returns:
            List of new child nodes created
        """
        if depth >= self.max_depth:
            logger.debug(f"Max depth {self.max_depth} reached, stopping expansion")
            return []

        # Generate candidate edits
        candidates = await self.propose_edits(
            code=node.code,
            task=task,
            parent_id=node.node_id,
            n=self.n_proposals
        )

        # Score with CMP
        scored_candidates = await self.cmp_score(candidates, task)

        # Select top-K
        selected = await self.select_best(scored_candidates, k=self.top_k)

        # Create child nodes
        children = []
        for candidate, cmp_score in selected:
            child_node = TreeNode(
                node_id=candidate.edit_id,
                code=candidate.code,
                hypothesis=candidate.hypothesis,
                cmp_score=cmp_score,
                judge_scores=cmp_score.judge_scores,
                parent_id=node.node_id,
                metadata=candidate.metadata
            )

            node.add_child(child_node)
            self.nodes[child_node.node_id] = child_node
            children.append(child_node)

            logger.debug(
                f"Created child node {child_node.node_id[:8]} "
                f"with CMP={cmp_score.cmp_score:.1f}"
            )

        return children

    async def search(
        self,
        initial_code: str,
        task: str,
        max_iterations: int = 5
    ) -> TreeNode:
        """
        Perform tree search to find best code version

        Args:
            initial_code: Starting code
            task: Task description
            max_iterations: Maximum search iterations

        Returns:
            Best node found (highest CMP score)
        """
        logger.info(f"Starting HGM tree search for {max_iterations} iterations")

        # Create root node
        self.root = TreeNode(
            node_id="root",
            code=initial_code,
            hypothesis="Initial version",
            metadata={"depth": 0}
        )
        self.nodes[self.root.node_id] = self.root

        # Score root
        root_score = await self.judge.score_output(
            output=initial_code,
            criteria=task,
            context={}
        )
        self.root.cmp_score = self.judge.calculate_cmp_score([root_score])
        self.root.judge_scores = [root_score]

        logger.info(f"Root CMP score: {self.root.cmp_score.cmp_score:.1f}")

        best_node = self.root
        best_score = self.root.cmp_score.cmp_score

        for iteration in range(max_iterations):
            logger.info(f"Iteration {iteration + 1}/{max_iterations}")

            # Select node to expand (highest CMP score among leaves)
            leaf_nodes = [n for n in self.nodes.values() if n.is_leaf]
            if not leaf_nodes:
                logger.info("No leaf nodes to expand, stopping")
                break

            # Expand best leaf
            node_to_expand = max(leaf_nodes, key=lambda n: n.mean_score)
            logger.info(
                f"Expanding node {node_to_expand.node_id[:8]} "
                f"with CMP={node_to_expand.mean_score:.1f}"
            )

            children = await self.expand_tree(
                node=node_to_expand,
                task=task,
                depth=iteration
            )

            # Update best node
            for child in children:
                if child.mean_score > best_score:
                    best_node = child
                    best_score = child.mean_score
                    logger.info(
                        f"New best node: {best_node.node_id[:8]} "
                        f"with CMP={best_score:.1f}"
                    )

            # Early stopping if best score exceeds threshold
            if best_score >= self.cmp_threshold:
                logger.info(
                    f"CMP score {best_score:.1f} exceeds threshold {self.cmp_threshold}, "
                    f"stopping early"
                )
                break

        logger.info(
            f"Search complete: best CMP score = {best_score:.1f}, "
            f"total nodes = {len(self.nodes)}"
        )

        return best_node

    def get_best_path(self, node: TreeNode) -> List[TreeNode]:
        """
        Get path from root to given node

        Args:
            node: Target node

        Returns:
            List of nodes from root to target
        """
        path = [node]
        current = node
        while current.parent_id:
            parent = self.nodes.get(current.parent_id)
            if parent:
                path.append(parent)
                current = parent
            else:
                break

        return list(reversed(path))


# Singleton instance
_oracle_hgm: Optional[OracleHGM] = None


def get_oracle_hgm(
    llm_client: Optional[LLMClient] = None,
    judge: Optional[AgentJudge] = None,
    trajectory_pool: Optional[TrajectoryPool] = None,
    n_proposals: int = 10,
    top_k: int = 3,
    max_depth: int = 5,
    cmp_threshold: float = 70.0
) -> OracleHGM:
    """
    Get or create singleton OracleHGM instance

    Args:
        llm_client: LLM for generating hypotheses (defaults to GPT-4o)
        judge: Agent-as-a-Judge for scoring
        trajectory_pool: Pool for archiving best solutions
        n_proposals: Number of candidates per iteration
        top_k: Number of top candidates to expand
        max_depth: Maximum tree depth
        cmp_threshold: Minimum CMP score to archive

    Returns:
        OracleHGM instance
    """
    global _oracle_hgm
    if _oracle_hgm is None:
        # Create default LLM client if not provided
        if llm_client is None:
            llm_client = LLMFactory.create(LLMProvider.GPT4O)

        _oracle_hgm = OracleHGM(
            llm_client=llm_client,
            judge=judge,
            trajectory_pool=trajectory_pool,
            n_proposals=n_proposals,
            top_k=top_k,
            max_depth=max_depth,
            cmp_threshold=cmp_threshold
        )
    return _oracle_hgm
