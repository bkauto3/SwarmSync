"""
Memory Router for Genesis LangGraph Store

Provides intelligent routing and cross-namespace querying for Genesis memory system.
Enables complex queries spanning multiple namespaces with aggregation and filtering.

Research Sources (via Context7 MCP):
- LangGraph Store API Documentation (Context7: /langchain-ai/langgraph)
  Key insights: BaseStore interface requirements, namespace design patterns, TTL configuration
- MongoDB Aggregation Framework (Context7: /mongodb/docs)
  Key insights: Cross-namespace query optimization, index strategies
- Memory Router Patterns (Context7 research)
  Key insights: Cross-namespace pattern matching, consensus building

Features:
- Cross-namespace search (e.g., find patterns across agent + business namespaces)
- Memory aggregation for consensus building
- Query optimization for common patterns
- Namespace-aware filtering and ranking

Use Cases:
1. "Find all successful Legal agent patterns used in e-commerce businesses"
   -> Cross-namespace: consensus (Legal patterns) + business (e-commerce filter)

2. "Get recent QA agent evolutions from last 7 days"
   -> Single namespace: evolution, time-filtered

3. "Retrieve permanent consensus patterns for deployment best practices"
   -> Single namespace: consensus, category-filtered

Version: 1.0
Created: November 2, 2025
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from infrastructure.langgraph_store import GenesisLangGraphStore

logger = logging.getLogger(__name__)


class MemoryRouter:
    """
    Intelligent router for cross-namespace memory queries.

    Provides high-level query patterns for common memory operations across
    the Genesis multi-agent system, with support for filtering, aggregation,
    and consensus building.

    Usage:
        router = MemoryRouter(store)

        # Cross-namespace query
        results = await router.find_agent_patterns_in_businesses(
            agent_type="Legal",
            business_category="e-commerce"
        )

        # Time-based query
        recent = await router.get_recent_evolutions(
            agent_name="qa_agent",
            days=7
        )

        # Consensus patterns
        patterns = await router.get_consensus_patterns(
            category="deployment"
        )
    """

    def __init__(self, store: GenesisLangGraphStore):
        """
        Initialize memory router.

        Args:
            store: GenesisLangGraphStore instance
        """
        self.store = store
        logger.info("Initialized MemoryRouter")

    async def find_agent_patterns_in_businesses(
        self,
        agent_type: str,
        business_category: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Find agent patterns used in specific business categories.

        Cross-namespace query combining consensus patterns with business data.

        Example:
            # Find Legal agent patterns in e-commerce businesses
            results = await router.find_agent_patterns_in_businesses(
                agent_type="Legal",
                business_category="e-commerce"
            )

        Args:
            agent_type: Agent type to search (e.g., "Legal", "QA", "Support")
            business_category: Optional business category filter
            limit: Maximum results to return

        Returns:
            List of matching patterns with metadata
        """
        logger.info(
            f"Cross-namespace query: agent_type={agent_type}, "
            f"business_category={business_category}"
        )

        # Step 1: Get consensus patterns for this agent type
        consensus_results = await self.store.search(
            namespace=("consensus", agent_type.lower()),
            query={"value.pattern_type": {"$exists": True}},
            limit=limit
        )

        # Step 2: If business category specified, filter by businesses using these patterns
        if business_category:
            # Get all businesses in this category
            business_results = await self.store.search(
                namespace=("business", business_category),
                limit=limit
            )

            # Cross-reference: find patterns used in these businesses
            business_pattern_ids = set()
            for business in business_results:
                if "used_patterns" in business.get("value", {}):
                    business_pattern_ids.update(business["value"]["used_patterns"])

            # Filter consensus patterns by business usage
            filtered_patterns = [
                pattern for pattern in consensus_results
                if pattern.get("key") in business_pattern_ids
            ]

            logger.info(
                f"Found {len(filtered_patterns)} patterns used in {business_category} businesses"
            )
            return filtered_patterns
        else:
            logger.info(f"Found {len(consensus_results)} consensus patterns for {agent_type}")
            return consensus_results

    async def get_recent_evolutions(
        self,
        agent_name: str,
        days: int = 7,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent evolution logs for an agent.

        Time-filtered query on evolution namespace.

        Example:
            # Get QA agent evolutions from last 7 days
            recent = await router.get_recent_evolutions(
                agent_name="qa_agent",
                days=7
            )

        Args:
            agent_name: Name of the agent (e.g., "qa_agent")
            days: Number of days to look back
            limit: Maximum results to return

        Returns:
            List of evolution entries sorted by timestamp
        """
        logger.info(f"Time-filtered query: agent={agent_name}, days={days}")

        # Calculate cutoff time
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Query evolution namespace with time filter
        results = await self.store.search(
            namespace=("evolution", agent_name),
            query={"created_at": {"$gte": cutoff}},
            limit=limit
        )

        # Sort by created_at (most recent first)
        sorted_results = sorted(
            results,
            key=lambda x: x.get("created_at", datetime.min.replace(tzinfo=timezone.utc)),
            reverse=True
        )

        logger.info(f"Found {len(sorted_results)} evolution entries in last {days} days")
        return sorted_results

    async def get_consensus_patterns(
        self,
        category: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve consensus patterns (permanent memory).

        Query consensus namespace with optional category and confidence filtering.

        Example:
            # Get deployment best practices with high confidence
            patterns = await router.get_consensus_patterns(
                category="deployment",
                min_confidence=0.8
            )

        Args:
            category: Optional category filter (e.g., "deployment", "testing")
            min_confidence: Minimum confidence score (0.0-1.0)
            limit: Maximum results to return

        Returns:
            List of consensus patterns
        """
        logger.info(f"Consensus query: category={category}, min_confidence={min_confidence}")

        if category:
            namespace = ("consensus", category)
        else:
            # Get all consensus namespaces
            all_namespaces = await self.store.list_namespaces(prefix=("consensus",))
            results = []

            for namespace in all_namespaces:
                namespace_results = await self.store.search(
                    namespace=namespace,
                    limit=limit
                )
                results.extend(namespace_results)

            # Apply confidence filter
            if min_confidence > 0.0:
                results = [
                    r for r in results
                    if r.get("value", {}).get("confidence", 0.0) >= min_confidence
                ]

            logger.info(f"Found {len(results)} consensus patterns")
            return results[:limit]

        # Single category query
        results = await self.store.search(namespace=namespace, limit=limit)

        # Apply confidence filter
        if min_confidence > 0.0:
            results = [
                r for r in results
                if r.get("value", {}).get("confidence", 0.0) >= min_confidence
            ]

        logger.info(f"Found {len(results)} consensus patterns in category '{category}'")
        return results

    async def aggregate_agent_metrics(
        self,
        agent_names: Optional[List[str]] = None,
        metric_keys: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Aggregate metrics across multiple agents.

        Useful for comparing agent performance or building dashboards.

        Example:
            # Compare QA and Support agent accuracy
            metrics = await router.aggregate_agent_metrics(
                agent_names=["qa_agent", "support_agent"],
                metric_keys=["accuracy", "latency_ms"]
            )

        Args:
            agent_names: List of agent names (None = all agents)
            metric_keys: List of metric keys to aggregate (None = all metrics)

        Returns:
            Dict mapping agent_name -> metric_key -> aggregated_value
        """
        logger.info(f"Aggregating metrics: agents={agent_names}, keys={metric_keys}")

        # Get all agent namespaces if not specified
        if agent_names is None:
            all_namespaces = await self.store.list_namespaces(prefix=("agent",))
            agent_names = [ns[1] for ns in all_namespaces if len(ns) > 1]

        aggregated = {}

        for agent_name in agent_names:
            # Get all metrics for this agent
            results = await self.store.search(
                namespace=("agent", agent_name),
                query={"value.metrics": {"$exists": True}}
            )

            # Aggregate metrics
            agent_metrics = defaultdict(list)
            for result in results:
                metrics = result.get("value", {}).get("metrics", {})
                for key, value in metrics.items():
                    if metric_keys is None or key in metric_keys:
                        if isinstance(value, (int, float)):
                            agent_metrics[key].append(value)

            # Calculate averages
            aggregated[agent_name] = {
                key: sum(values) / len(values) if values else 0.0
                for key, values in agent_metrics.items()
            }

        logger.info(f"Aggregated metrics for {len(aggregated)} agents")
        return aggregated

    async def search_across_namespaces(
        self,
        namespaces: List[Tuple[str, ...]],
        query: Optional[Dict[str, Any]] = None,
        limit_per_namespace: int = 50
    ) -> Dict[Tuple[str, ...], List[Dict[str, Any]]]:
        """
        Search across multiple namespaces in parallel.

        Low-level utility for custom cross-namespace queries.

        Example:
            # Search agent and business namespaces simultaneously
            results = await router.search_across_namespaces(
                namespaces=[
                    ("agent", "qa_agent"),
                    ("business", "biz_123")
                ],
                query={"value.status": "active"}
            )

        Args:
            namespaces: List of namespace tuples to search
            query: MongoDB query dict (optional)
            limit_per_namespace: Max results per namespace

        Returns:
            Dict mapping namespace -> results list
        """
        logger.info(f"Parallel search across {len(namespaces)} namespaces")

        # Create search tasks
        tasks = []
        for namespace in namespaces:
            task = self.store.search(
                namespace=namespace,
                query=query,
                limit=limit_per_namespace
            )
            tasks.append(task)

        # Execute in parallel
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        # Map results to namespaces
        results_map = {}
        for namespace, results in zip(namespaces, results_lists):
            if isinstance(results, Exception):
                logger.warning(f"Error searching {namespace}: {results}")
                results_map[namespace] = []
            else:
                results_map[namespace] = results

        total_results = sum(len(r) for r in results_map.values())
        logger.info(f"Found {total_results} total results across namespaces")
        return results_map

    async def get_namespace_summary(
        self,
        namespace_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get summary statistics for namespace(s).

        Useful for monitoring memory usage and health.

        Example:
            # Get summary for all agent namespaces
            summary = await router.get_namespace_summary(namespace_type="agent")

        Args:
            namespace_type: Type of namespace (None = all types)

        Returns:
            Dict with namespace statistics
        """
        logger.info(f"Getting namespace summary: type={namespace_type}")

        if namespace_type:
            namespaces = await self.store.list_namespaces(prefix=(namespace_type,))
        else:
            namespaces = await self.store.list_namespaces()

        summary = {
            "total_namespaces": len(namespaces),
            "by_type": defaultdict(int),
            "details": []
        }

        for namespace in namespaces:
            namespace_type_local = namespace[0] if namespace else "unknown"
            summary["by_type"][namespace_type_local] += 1

            # Get entry count for this namespace
            entries = await self.store.search(namespace=namespace, limit=1000)

            summary["details"].append({
                "namespace": namespace,
                "entry_count": len(entries),
                "ttl_policy": self.store._get_ttl_for_namespace(namespace)
            })

        logger.info(f"Namespace summary: {summary['total_namespaces']} total namespaces")
        return summary

    async def find_related_memories(
        self,
        namespace: Tuple[str, ...],
        key: str,
        relation_field: str = "related_to",
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Find related memories by following relationship links.

        Performs graph traversal to find connected memories.

        Example:
            # Find all memories related to a deployment pattern
            related = await router.find_related_memories(
                namespace=("consensus", "deployment"),
                key="pattern_123",
                relation_field="related_to",
                max_depth=3
            )

        Args:
            namespace: Starting namespace
            key: Starting key
            relation_field: Field name containing related keys
            max_depth: Maximum traversal depth

        Returns:
            List of related memory entries
        """
        logger.info(f"Finding related memories: {namespace}:{key}, max_depth={max_depth}")

        visited: Set[Tuple[Tuple[str, ...], str]] = set()
        related_memories: List[Dict[str, Any]] = []

        async def traverse(current_namespace: Tuple[str, ...], current_key: str, depth: int):
            if depth > max_depth:
                return

            # Mark as visited
            visit_key = (current_namespace, current_key)
            if visit_key in visited:
                return
            visited.add(visit_key)

            # Get current memory
            memory = await self.store.get(current_namespace, current_key)
            if not memory:
                return

            related_memories.append({
                "namespace": current_namespace,
                "key": current_key,
                "value": memory,
                "depth": depth
            })

            # Find related keys
            related_keys = memory.get(relation_field, [])
            if isinstance(related_keys, str):
                related_keys = [related_keys]

            # Traverse related memories
            for related_key in related_keys:
                await traverse(current_namespace, related_key, depth + 1)

        # Start traversal
        await traverse(namespace, key, 0)

        logger.info(f"Found {len(related_memories)} related memories (max_depth={max_depth})")
        return related_memories


# Singleton instance for global access
_router_instance: Optional[MemoryRouter] = None


def get_memory_router(store: Optional[GenesisLangGraphStore] = None) -> MemoryRouter:
    """
    Get or create singleton MemoryRouter instance.

    Args:
        store: Optional GenesisLangGraphStore instance

    Returns:
        Singleton router instance
    """
    global _router_instance

    if _router_instance is None:
        if store is None:
            from infrastructure.langgraph_store import get_store
            store = get_store()
        _router_instance = MemoryRouter(store)

    return _router_instance
