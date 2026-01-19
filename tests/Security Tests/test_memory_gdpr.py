"""Compliance layer tests for GDPR and PII protection."""

import asyncio
from typing import Any, Dict, List, Optional, Tuple

import pytest

from infrastructure.memory.compliance_layer import MemoryComplianceLayer


class DummyStore:
    VALID_NAMESPACE_TYPES = {"agent", "business"}

    def __init__(self):
        self.data: Dict[Tuple[str, ...], Dict[str, Dict[str, Any]]] = {}
        self.deleted: List[Tuple[Tuple[str, ...], str]] = []

    def _get_ttl_for_namespace(self, namespace: Tuple[str, ...]) -> Optional[int]:
        mapping = {
            "agent": 7 * 24 * 60 * 60,
            "business": 90 * 24 * 60 * 60,
        }
        return mapping.get(namespace[0])

    async def search(
        self,
        namespace: Tuple[str, ...],
        query: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        actor: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        entries = self.data.get(namespace, {})
        results = []
        for key, document in entries.items():
            if query and query.get("metadata.user_id"):
                expected_user = query["metadata.user_id"]
                if document.get("metadata", {}).get("user_id") != expected_user:
                    continue
            results.append({"key": key, **document})
            if len(results) >= limit:
                break
        return results

    async def delete(
        self,
        namespace: Tuple[str, ...],
        key: str,
        actor: Optional[str] = None,
    ) -> bool:
        namespace_entries = self.data.setdefault(namespace, {})
        if key in namespace_entries:
            del namespace_entries[key]
            self.deleted.append((namespace, key))
            return True
        return False


@pytest.fixture
def compliance_layer():
    store = DummyStore()
    return MemoryComplianceLayer(store), store


def test_pii_redaction(compliance_layer):
    layer, _ = compliance_layer
    namespace = ("agent", "qa_agent")
    value = {
        "summary": "Contact Name: John Doe via john.doe@example.com or +1-555-123-4567",
        "notes": [
            "SSN 123-45-6789 should never be stored",
        ],
    }
    metadata: Dict[str, Any] = {"user_id": "user-1"}

    sanitized, updated_metadata = layer.before_write(namespace, "contact", value, metadata, actor="auditor")

    assert "[REDACTED:email]" in sanitized["summary"]
    assert "[REDACTED:phone]" in sanitized["summary"]
    assert "[REDACTED:ssn]" in sanitized["notes"][0]

    pii_entries = updated_metadata["compliance"]["pii_findings"]
    categories = {entry["category"] for entry in pii_entries}
    assert categories >= {"email", "phone", "ssn"}
    assert updated_metadata["compliance"]["last_modified_by"] == "auditor"
    assert "retention_expires_at" in updated_metadata["compliance"]


def test_gdpr_delete_workflow(compliance_layer):
    layer, store = compliance_layer
    namespace = ("agent", "qa_agent")
    store.data[namespace] = {
        "key1": {
            "value": {"text": "hello"},
            "metadata": {"user_id": "user-42"},
        },
        "key2": {
            "value": {"text": "other"},
            "metadata": {"user_id": "user-42"},
        },
    }

    deleted = asyncio.run(layer.delete_user_data("user-42", [namespace]))
    assert deleted == 2
    assert store.deleted == [(namespace, "key1"), (namespace, "key2")]


def test_query_sanitisation_blocks_unsafe_operator(compliance_layer):
    layer, _ = compliance_layer
    with pytest.raises(ValueError):
        layer.sanitize_query({"$where": "this.value == 'x'"})


def test_audit_logging_records_access(compliance_layer):
    layer, _ = compliance_layer
    namespace = ("agent", "qa_agent")
    layer.record_access(namespace, "key", actor="qa_agent", action="read")

    log = layer.get_access_log()
    assert log[0]["actor"] == "qa_agent"
    assert log[0]["action"] == "read"
