import asyncio
import json
import math
import re
from typing import Dict, List, Tuple

import numpy as np
import pytest

from infrastructure.memory.agentic_rag import (
    AgenticRAG,
    AgenticRAGStats,
    RetrievalMode,
    RetrievalResult,
)
from infrastructure.memory_store import MemoryEntry, MemoryMetadata


VOCAB = [
    "auth",
    "jwt",
    "billing",
    "analytics",
    "support",
    "deployment",
]


class FakeEmbeddingService:
    """Deterministic embedding service for tests."""

    def __init__(self):
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    def _embed(self, text: str) -> List[float]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        vector = [tokens.count(term) for term in VOCAB]
        vector.append(len(tokens))
        norm = np.linalg.norm(vector)
        if norm == 0:
            return [0.0 for _ in vector]
        return (np.array(vector) / norm).tolist()

    async def embed_text(self, text: str) -> List[float]:
        return self._embed(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]


class FakeMongoBackend:
    """In-memory stand-in for MongoDBBackend."""

    def __init__(self):
        self.storage: Dict[Tuple[str, str], Dict[str, MemoryEntry]] = {}

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def put(
        self,
        namespace: Tuple[str, str],
        key: str,
        value: Dict,
        metadata: MemoryMetadata | None = None,
    ) -> MemoryEntry:
        metadata = metadata or MemoryMetadata()
        entry = MemoryEntry(namespace=namespace, key=key, value=value, metadata=metadata)
        self.storage.setdefault(namespace, {})[key] = entry
        return entry

    async def get(self, namespace: Tuple[str, str], key: str) -> MemoryEntry | None:
        entry = self.storage.get(namespace, {}).get(key)
        if entry is None:
            return None
        return MemoryEntry.from_dict(entry.to_dict())

    async def search(
        self,
        namespace: Tuple[str, str],
        query: str,
        limit: int = 1000,
    ) -> List[MemoryEntry]:
        ns_type, ns_id = namespace
        matches: List[MemoryEntry] = []
        for stored_ns, entries in self.storage.items():
            stored_type, stored_id = stored_ns
            if ns_type != "*" and stored_type != ns_type:
                continue
            if ns_id != "*" and stored_id != ns_id:
                continue
            matches.extend(MemoryEntry.from_dict(entry.to_dict()) for entry in entries.values())
        return matches[:limit]


@pytest.fixture
async def rag():
    service = FakeEmbeddingService()
    backend = FakeMongoBackend()
    instance = AgenticRAG(
        embedding_service=service,
        mongodb_backend=backend,
        compression_enabled=True,
        compression_threshold=10,
    )
    await instance.connect()
    yield instance
    await instance.disconnect()


@pytest.mark.asyncio
async def test_vector_search_ranks_by_similarity(rag: AgenticRAG):
    await rag.store_memory(
        ("agent", "qa"),
        "auth_tests",
        {"description": "Authentication regression tests using JWT tokens"},
    )
    await rag.store_memory(
        ("agent", "billing"),
        "invoice_pipeline",
        {"description": "Recurring billing workflow and invoice generation"},
    )

    results = await rag.retrieve(
        "JWT authentication flow",
        mode=RetrievalMode.VECTOR_ONLY,
        top_k=1,
    )

    assert results
    assert results[0].entry.key == "auth_tests"
    assert results[0].score > 0.95


@pytest.mark.asyncio
async def test_vector_search_includes_business_namespace(rag: AgenticRAG):
    await rag.store_memory(
        ("business", "saas_001"),
        "retention_playbook",
        {"description": "Customer retention strategy and runbook"},
    )
    await rag.store_memory(
        ("agent", "marketing"),
        "campaign_notes",
        {"description": "Lifecycle campaign notes"},
    )

    results = await rag.retrieve(
        "retention strategy",
        mode=RetrievalMode.VECTOR_ONLY,
        top_k=2,
    )

    keys = {result.entry.key for result in results}
    assert "retention_playbook" in keys


@pytest.mark.asyncio
async def test_graph_traversal_returns_related_nodes(rag: AgenticRAG):
    await rag.store_memory(
        ("agent", "builder"),
        "auth_impl",
        {"description": "JWT auth implementation"},
    )
    await rag.store_memory(
        ("agent", "qa"),
        "auth_tests",
        {"description": "Authentication regression tests"},
        relationships={"depends_on": [("agent:builder", "auth_impl")]},
    )

    start = [("agent:qa", "auth_tests")]
    results = await rag.retrieve(
        query="ignored",
        mode=RetrievalMode.GRAPH_ONLY,
        start_nodes=start,
        top_k=2,
    )

    keys = {result.entry.key for result in results}
    assert keys == {"auth_tests", "auth_impl"}


@pytest.mark.asyncio
async def test_hybrid_retrieval_merges_vector_and_graph(rag: AgenticRAG):
    await rag.store_memory(
        ("agent", "billing"),
        "billing_runbook",
        {"description": "Billing troubleshooting guide"},
        relationships={"used_by": [("agent:support", "support_playbook")]},
    )
    await rag.store_memory(
        ("agent", "support"),
        "support_playbook",
        {"description": "Support escalation procedures for billing issues"},
    )

    results = await rag.retrieve(
        "billing support escalation",
        mode=RetrievalMode.HYBRID,
        top_k=2,
    )

    keys = [result.entry.key for result in results]
    assert "billing_runbook" in keys
    assert "support_playbook" in keys


@pytest.mark.asyncio
async def test_compression_reduces_payload_size(rag: AgenticRAG):
    original = {"description": "configuration parameters", "implementation": "detailed plan"}
    entry_id = await rag.store_memory(
        ("agent", "ops"),
        "deployment_playbook",
        original,
    )

    # Fetch raw stored entry from backend to inspect compression
    stored = await rag.mongodb_backend.get(("agent", "ops"), "deployment_playbook")
    assert stored is not None
    assert "desc" in stored.value  # compressed key
    assert len(json.dumps(stored.value)) < len(json.dumps(original))

    retrieved = await rag.retrieve(
        "deployment",
        mode=RetrievalMode.VECTOR_ONLY,
        namespace_filter=("agent", "ops"),
        top_k=1,
    )
    assert retrieved[0].entry.value["description"] == original["description"]


@pytest.mark.asyncio
async def test_stats_tracking(rag: AgenticRAG):
    await rag.store_memory(
        ("agent", "analytics"),
        "dashboard_metrics",
        {"description": "Analytics dashboard metrics and alerting"},
    )

    await rag.retrieve("dashboard analytics", mode=RetrievalMode.VECTOR_ONLY, top_k=1)
    stats = rag.get_stats()

    assert isinstance(stats, AgenticRAGStats)
    assert stats.vector_searches == 1
    assert stats.total_results >= 1
