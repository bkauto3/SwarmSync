"""Compliance layer for Genesis memory system.

The compliance layer adds GDPR/CCPA guardrails around LangGraph store usage by
providing:
- PII detection/redaction before writes
- Right-to-delete workflows (Article 17)
- Retention policy tagging based on namespace TTL configuration
- Audit logging helpers for access tracking
- Query sanitisation to mitigate memory query injection attacks

The implementation intentionally keeps runtime dependencies minimal so it can
run in sandboxed unit tests without MongoDB. The layer can operate in pure
Python by introspecting nested dict/list payloads.
"""

from __future__ import annotations

import copy
import json
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)


PII_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PII_PHONE = re.compile(r"(\+?\d[\d\-\s]{7,}\d)")
PII_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
PII_CREDIT_CARD = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
PII_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PII_NAME_HINT = re.compile(r"\b(Name|Contact|Full Name):\s*(?P<name>[A-Z][a-z]+\s+[A-Z][a-z]+)\b")

SAFE_MONGO_OPERATORS = {
    "$eq",
    "$ne",
    "$gt",
    "$gte",
    "$lt",
    "$lte",
    "$in",
    "$nin",
    "$exists",
    "$regex",
    "$and",
    "$or",
    "$not",
    "$size",
    "$all",
    "$elemMatch",
}


@dataclass
class MemoryPIIFinding:
    """Represents a detected PII span inside a nested payload."""

    path: str
    category: str
    value: str
    confidence: float = 0.95

    def to_metadata(self) -> Dict[str, Any]:
        data = asdict(self)
        # mask the raw value in metadata to avoid leaking sensitive data
        data["value"] = "[REDACTED]"
        return data


class MemoryComplianceLayer:
    """Compliance helper attached to the LangGraph store.

    The layer does not perform I/O itself; instead it coordinates with the
    store that owns it. Methods that touch persistence return enriched metadata
    so the caller can persist it in the same Mongo document.
    """

    def __init__(self, store: Any):
        self.store = store
        self._access_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # PII detection / sanitisation
    # ------------------------------------------------------------------
    def before_write(
        self,
        namespace: Tuple[str, ...],
        key: str,
        value: Dict[str, Any],
        metadata: Dict[str, Any],
        actor: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Scan payload for PII, redact if necessary, and annotate metadata."""

        findings = self._scan_for_pii(value)
        sanitized_value = copy.deepcopy(value)

        if findings:
            self._redact_value_in_place(sanitized_value, findings)
            metadata.setdefault("compliance", {})
            metadata["compliance"].setdefault("pii_findings", [])
            metadata["compliance"]["pii_findings"].extend(
                [finding.to_metadata() for finding in findings]
            )
            metadata["compliance"]["pii_redacted"] = True
            logger.info(
                "PII detected for namespace=%s key=%s categories=%s",
                namespace,
                key,
                {finding.category for finding in findings},
            )
        else:
            metadata.setdefault("compliance", {})
            metadata["compliance"].setdefault("pii_findings", [])
            metadata["compliance"]["pii_redacted"] = False

        # Retention tagging based on TTL policy
        retention_seconds = None
        if hasattr(self.store, "_get_ttl_for_namespace"):
            retention_seconds = self.store._get_ttl_for_namespace(namespace)

        if retention_seconds:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=retention_seconds)
            metadata["compliance"]["retention_expires_at"] = expires_at.isoformat()
        else:
            metadata["compliance"].pop("retention_expires_at", None)

        if actor:
            metadata["compliance"]["last_modified_by"] = actor

        return sanitized_value, metadata

    def _scan_for_pii(self, value: Any, path: str = "") -> List[MemoryPIIFinding]:
        findings: List[MemoryPIIFinding] = []

        if isinstance(value, dict):
            for key, nested in value.items():
                child_path = f"{path}.{key}" if path else key
                findings.extend(self._scan_for_pii(nested, child_path))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                child_path = f"{path}[{index}]"
                findings.extend(self._scan_for_pii(item, child_path))
        elif isinstance(value, str):
            findings.extend(self._detect_in_string(value, path))

        return findings

    def _detect_in_string(self, text: str, path: str) -> List[MemoryPIIFinding]:
        matches: List[MemoryPIIFinding] = []

        for regex, category in (
            (PII_EMAIL, "email"),
            (PII_SSN, "ssn"),
            (PII_CREDIT_CARD, "credit_card"),
            (PII_PHONE, "phone"),
            (PII_IP, "ip_address"),
        ):
            for match in regex.finditer(text):
                matches.append(
                    MemoryPIIFinding(
                        path=path,
                        category=category,
                        value=match.group(0),
                        confidence=0.95,
                    )
                )

        name_hint = PII_NAME_HINT.search(text)
        if name_hint:
            matches.append(
                MemoryPIIFinding(
                    path=path,
                    category="personal_name",
                    value=name_hint.group("name"),
                    confidence=0.6,
                )
            )

        return matches

    def _redact_value_in_place(self, payload: Any, findings: Iterable[MemoryPIIFinding]) -> None:
        """Redact detected PII values inside the nested payload."""

        findings_by_path: Dict[str, List[MemoryPIIFinding]] = {}
        for finding in findings:
            findings_by_path.setdefault(finding.path, []).append(finding)

        def redact(node: Any, path: str = ""):
            if isinstance(node, dict):
                for key, nested in node.items():
                    child_path = f"{path}.{key}" if path else key
                    node[key] = redact(nested, child_path)
                return node
            if isinstance(node, list):
                for idx, item in enumerate(node):
                    child_path = f"{path}[{idx}]"
                    node[idx] = redact(item, child_path)
                return node
            if isinstance(node, str):
                replacements = findings_by_path.get(path, [])
                redacted_text = node
                for finding in replacements:
                    redacted_text = redacted_text.replace(
                        finding.value,
                        f"[REDACTED:{finding.category}]",
                    )
                return redacted_text
            return node

        redact(payload)

    # ------------------------------------------------------------------
    # GDPR Article 17: Right to delete
    # ------------------------------------------------------------------
    async def delete_user_data(
        self,
        user_identifier: str,
        namespaces: Optional[List[Tuple[str, ...]]] = None,
    ) -> int:
        """Delete all memories associated with a user identifier.

        Returns the number of documents deleted.
        """

        if not hasattr(self.store, "search") or not hasattr(self.store, "delete"):
            raise RuntimeError("Store does not support search/delete APIs required for erasure")

        namespaces_to_check: List[Tuple[str, ...]]
        if namespaces is None:
            namespaces_to_check = []
            if hasattr(self.store, "VALID_NAMESPACE_TYPES"):
                for namespace_type in getattr(self.store, "VALID_NAMESPACE_TYPES"):
                    namespaces_to_check.append((namespace_type, "*"))
            else:
                namespaces_to_check = [("agent", "*")]
        else:
            namespaces_to_check = namespaces

        deleted = 0
        for namespace in namespaces_to_check:
            try:
                results = await self.store.search(
                    namespace,
                    {"metadata.user_id": user_identifier},
                    limit=1000,
                )
            except Exception as exc:  # pragma: no cover - store may not support wildcard namespace
                logger.warning("Skipping namespace %s during erasure: %s", namespace, exc)
                continue

            for entry in results:
                key = entry["key"]
                if await self.store.delete(namespace, key):
                    deleted += 1
                    self.record_access(namespace, key, actor="gdpr_erasure", action="delete")

        logger.info("GDPR erasure processed for %s, deleted=%s", user_identifier, deleted)
        return deleted

    # ------------------------------------------------------------------
    # Audit logging helpers
    # ------------------------------------------------------------------
    def record_access(
        self,
        namespace: Tuple[str, ...],
        key: str,
        actor: Optional[str],
        action: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "namespace": list(namespace),
            "key": key,
            "actor": actor or "unknown",
            "action": action,
            "metadata": metadata or {},
        }
        self._access_log.append(entry)
        logger.debug("Memory access logged: %s", entry)

    def get_access_log(self) -> List[Dict[str, Any]]:
        return list(self._access_log)

    # ------------------------------------------------------------------
    # Query sanitisation
    # ------------------------------------------------------------------
    def sanitize_query(self, query: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if query is None:
            return None
        self._validate_query_dict(query)
        return query

    def _validate_query_dict(self, query: Dict[str, Any]) -> None:
        for key, value in query.items():
            if isinstance(key, str) and key.startswith("$") and key not in SAFE_MONGO_OPERATORS:
                raise ValueError(f"Unsafe MongoDB operator detected: {key}")
            if isinstance(value, dict):
                self._validate_query_dict(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._validate_query_dict(item)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def export_access_log_json(self) -> str:
        return json.dumps(self._access_log, indent=2)


__all__ = ["MemoryComplianceLayer", "MemoryPIIFinding"]
