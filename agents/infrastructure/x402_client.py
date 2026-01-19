"""
X402 Client
===========

Centralized helper for handling HTTP 402 payment flows, ledgering,
budget guardrails, and monitoring hooks.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import urlparse

import requests

from infrastructure.business_monitor import get_monitor
from infrastructure.x402_vendor_cache import get_x402_vendor_cache

logger = logging.getLogger(__name__)

try:  # Optional real SDK
    import x402
except Exception:  # pragma: no cover - best effort import
    x402 = None

ApprovalHandler = Callable[[Dict[str, Any]], Dict[str, Any]]

APPROVAL_HANDLER: Optional[ApprovalHandler] = None


def register_x402_approval_handler(handler: ApprovalHandler) -> None:
    """Allow Genesis Meta Agent to register a custom approval hook."""
    global APPROVAL_HANDLER
    APPROVAL_HANDLER = handler


class X402PaymentError(RuntimeError):
    """Raised when a payment cannot be executed (budget, SDK, or vendor error)."""


@dataclass(frozen=True)
class PaymentChallenge:
    amount: Decimal
    token: str
    chain: str
    recipient: str
    vendor: str
    url: str


@dataclass(frozen=True)
class PaymentReceipt:
    signature: str
    tx_hash: str
    token: str
    chain: str
    amount: Decimal


@dataclass(frozen=True)
class X402BudgetConfig:
    daily_limit_usdc: float
    max_payment_per_request: float


DEFAULT_X402_BUDGETS: Dict[str, X402BudgetConfig] = {
    "research_agent": X402BudgetConfig(daily_limit_usdc=25.0, max_payment_per_request=1.0),
    "builder_agent": X402BudgetConfig(daily_limit_usdc=40.0, max_payment_per_request=2.5),
    "deploy_agent": X402BudgetConfig(daily_limit_usdc=50.0, max_payment_per_request=5.0),
    "qa_agent": X402BudgetConfig(daily_limit_usdc=20.0, max_payment_per_request=1.5),
    "commerce_agent": X402BudgetConfig(daily_limit_usdc=60.0, max_payment_per_request=10.0),
}


class X402Client:
    """
    Shared helper that enforces budgets, signs payments, records ledger entries,
    and exposes convenience wrappers for HTTP requests.
    """

    def __init__(self, budgets: Optional[Dict[str, X402BudgetConfig]] = None):
        self.wallet_key = os.getenv("X402_WALLET_KEY")
        self.wallet_address = os.getenv("X402_WALLET_ADDRESS", "")
        self.rpc_url = os.getenv("X402_RPC_URL", "")
        self.use_fake = os.getenv("X402_USE_FAKE", "true").lower() in {"1", "true", "yes"}
        self.budgets = budgets or DEFAULT_X402_BUDGETS
        self.approval_threshold = Decimal(os.getenv("X402_APPROVAL_THRESHOLD", "10"))
        self._daily_spend: Dict[str, Dict[str, Decimal]] = {}
        self._ledger_lock = threading.Lock()
        self.ledger_path = Path("data/x402/transactions.jsonl")
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.monitor = None
        try:
            self.monitor = get_monitor()
            if self.monitor:
                self.monitor.register_x402_budgets(self.budgets)
        except Exception:
            logger.debug("Business monitor unavailable for x402 instrumentation", exc_info=True)
        self.vendor_cache = get_x402_vendor_cache()
        self._authorizations: Dict[str, Dict[str, Any]] = {}
        self._vendor_failure_streak: Dict[str, int] = {}
        self._wallet_start = float(os.getenv("X402_WALLET_START_USDC", "500"))
        self._wallet_remaining = self._wallet_start
        self._wallet_warned = False
        self.sdk_client = None
        if not self.use_fake and x402:
            try:
                self.sdk_client = x402.Client(
                    private_key=self.wallet_key,
                    rpc_url=self.rpc_url,
                )
            except Exception as exc:  # pragma: no cover - depends on sdk
                logger.warning("Failed to initialize x402 SDK client: %s", exc)
                self.use_fake = True

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def request_with_autopay(
        self,
        method: str,
        url: str,
        *,
        agent_name: str,
        vendor: Optional[str] = None,
        session: Optional[requests.Session] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Issue HTTP request that transparently retries when the server responds with
        HTTP 402 Payment Required. Only synchronous requests are supported today.
        """
        payment_metadata = kwargs.pop("payment_metadata", None)
        sess = session or requests.Session()
        response = sess.request(method, url, **kwargs)
        if response.status_code != 402:
            return response

        challenge = self._parse_challenge(response, url)
        merged_metadata = {**(metadata or {}), **(payment_metadata or {})}
        receipt = self._sign_payment(agent_name, challenge, merged_metadata)
        headers = dict(kwargs.get("headers") or {})
        headers["X-PAYMENT"] = receipt.signature
        headers["X-PAYMENT-TOKEN"] = receipt.token
        kwargs["headers"] = headers
        try:
            response = sess.request(method, url, **kwargs)
        except Exception as exc:
            self._record_transaction(
                agent_name=agent_name,
                vendor=vendor or challenge.vendor,
                challenge=challenge,
                receipt=None,
                metadata={**merged_metadata, "url": url, "error": str(exc)},
                mode="http_autopay",
                success=False,
            )
            raise
        if response.status_code == 402:
            self._record_transaction(
                agent_name=agent_name,
                vendor=vendor or challenge.vendor,
                challenge=challenge,
                receipt=receipt,
                metadata={**merged_metadata, "url": url},
                mode="http_autopay",
                success=False,
            )
            raise X402PaymentError(f"Vendor '{challenge.vendor}' rejected payment for {url}")
        self._record_transaction(
            agent_name=agent_name,
            vendor=vendor or challenge.vendor,
            challenge=challenge,
            receipt=receipt,
            metadata={**merged_metadata, "url": url},
            mode="http",
        )
        return response

    def record_manual_payment(
        self,
        *,
        agent_name: str,
        vendor: str,
        amount: float,
        token: str = "USDC",
        chain: str = "base",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentReceipt:
        """
        Record a manual (non-HTTP) spend such as LLM usage or premium API credits.
        """
        challenge = PaymentChallenge(
            amount=self._to_decimal(amount),
            token=token.upper(),
            chain=chain.lower(),
            recipient=self.wallet_address or "manual-ledger",
            vendor=vendor,
            url=metadata.get("url") if metadata else vendor,
        )
        receipt = self._sign_payment(agent_name, challenge, metadata)
        self._record_transaction(
            agent_name=agent_name,
            vendor=vendor,
            challenge=challenge,
            receipt=receipt,
            metadata=metadata,
            mode="manual",
        )
        return receipt

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _parse_challenge(self, response: requests.Response, url: str) -> PaymentChallenge:
        headers = response.headers or {}
        body: Dict[str, Any] = {}
        try:
            body = response.json()
        except ValueError:
            body = {}

        amount = (
            headers.get("X-PAYMENT-AMOUNT")
            or body.get("price")
            or body.get("payment_amount")
            or "0"
        )
        token_chain = headers.get("X-ACCEPT-PAYMENT") or body.get("accepted_tokens") or "usdc:base"
        token, chain = self._select_token_chain(token_chain)
        recipient = headers.get("X-PAYMENT-ADDRESS") or body.get("payment_address") or self.wallet_address
        vendor = headers.get("X-PAYMENT-VENDOR") or urlparse(url).netloc or "unknown-vendor"

        challenge = PaymentChallenge(
            amount=self._to_decimal(amount),
            token=token.upper(),
            chain=chain.lower(),
            recipient=recipient,
            vendor=vendor,
            url=url,
        )
        self.vendor_cache.record_observation(
            vendor,
            token=token,
            chain=chain,
            metadata={"url": url},
        )
        return challenge

    def _sign_payment(
        self,
        agent_name: str,
        challenge: PaymentChallenge,
        metadata: Optional[Dict[str, Any]],
        *,
        enforce_budget: bool = True,
    ) -> PaymentReceipt:
        self._require_approval(
            agent_name=agent_name,
            vendor=challenge.vendor,
            amount=challenge.amount,
            metadata=metadata,
        )
        if enforce_budget:
            self._enforce_budget(agent_name, challenge.amount)
        if self.use_fake:
            signature = f"fake-payment::{challenge.chain}::{uuid.uuid4()}"
            tx_hash = f"fake-tx::{int(time.time()*1000)}"
        else:  # pragma: no cover - depends on SDK availability
            if not self.sdk_client:
                raise X402PaymentError("x402 SDK client unavailable")
            try:
                payload = self.sdk_client.create_payment(
                    amount=str(challenge.amount),
                    token=challenge.token,
                    chain=challenge.chain,
                    recipient=challenge.recipient,
                    metadata=metadata or {},
                )
                signature = payload.signature
                tx_hash = payload.transaction_hash
            except Exception as exc:
                logger.error("x402 SDK payment failed: %s", exc)
                raise X402PaymentError(str(exc))

        return PaymentReceipt(
            signature=signature,
            tx_hash=tx_hash,
            token=challenge.token,
            chain=challenge.chain,
            amount=challenge.amount,
        )

    def _record_transaction(
        self,
        *,
        agent_name: str,
        vendor: str,
        challenge: Optional[PaymentChallenge],
        receipt: Optional[PaymentReceipt],
        metadata: Optional[Dict[str, Any]],
        mode: str,
        success: bool = True,
        authorization_id: Optional[str] = None,
    ) -> None:
        entry = {
            "timestamp": time.time(),
            "agent": agent_name,
            "vendor": vendor,
            "url": challenge.url if challenge else metadata.get("url") if metadata else None,
            "amount_usdc": float(challenge.amount) if challenge else float(metadata.get("amount_usdc", 0.0)) if metadata else 0.0,
            "token": receipt.token if receipt else metadata.get("token") if metadata else None,
            "chain": receipt.chain if receipt else metadata.get("chain") if metadata else None,
            "tx_hash": receipt.tx_hash if receipt else None,
            "signature": receipt.signature if receipt else None,
            "mode": mode,
            "success": success,
            "authorization_id": authorization_id,
            "metadata": metadata or {},
        }
        with self._ledger_lock:
            with self.ledger_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry) + os.linesep)
        if self.monitor:
            try:
                self.monitor.record_x402_payment(agent_name, entry)
            except Exception:
                logger.debug("Unable to write x402 event to monitor", exc_info=True)
        if challenge and success:
            try:
                self.vendor_cache.record_observation(
                    vendor,
                    token=challenge.token,
                    chain=challenge.chain,
                    price=float(challenge.amount),
                    metadata=metadata,
                )
            except Exception:
                logger.debug("Unable to update vendor cache for %s", vendor, exc_info=True)
        if success:
            self._vendor_failure_streak[vendor] = 0
        else:
            streak = self._vendor_failure_streak.get(vendor, 0) + 1
            self._vendor_failure_streak[vendor] = streak
            if streak >= 5:
                logger.warning("⚠️  %s payment failures for vendor %s", streak, vendor)
        self._update_wallet_balance(entry)

    def _update_wallet_balance(self, entry: Dict[str, Any]) -> None:
        if self._wallet_start <= 0 or not entry.get("success"):
            return
        self._wallet_remaining -= float(entry.get("amount_usdc", 0.0))
        if (
            not self._wallet_warned
            and self._wallet_remaining > 0
            and self._wallet_remaining < 50.0
        ):
            logger.warning(
                "⚠️  X402 wallet balance low: $%.2f remaining", self._wallet_remaining
            )
            self._wallet_warned = True

    def _require_approval(
        self,
        *,
        agent_name: str,
        vendor: str,
        amount: Decimal,
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        """Invoke the Genesis Meta Agent approval hook for large payments."""
        if amount <= self.approval_threshold or not APPROVAL_HANDLER:
            return
        intent = {
            "agent_name": agent_name,
            "vendor": vendor,
            "amount": float(amount),
            "metadata": metadata or {},
        }
        decision = APPROVAL_HANDLER(intent)
        if not decision.get("approved", True):
            reason = decision.get("reason", "x402 approval denied")
            self._record_transaction(
                agent_name=agent_name,
                vendor=vendor,
                challenge=None,
                receipt=None,
                metadata={**intent, "decision": decision},
                mode="approval_denied",
                success=False,
            )
            raise X402PaymentError(reason)

    def _select_token_chain(self, header_value: str) -> Tuple[str, str]:
        """
        Header may be CSV like 'usdc:base, eth:ethereum'. Pick the first.
        """
        first_value = (
            header_value[0]
            if isinstance(header_value, (list, tuple))
            else str(header_value).split(",")[0]
        )
        token_chain = first_value.strip().split(":")
        if len(token_chain) == 2:
            return token_chain[0], token_chain[1]
        return token_chain[0], "base"

    def _enforce_budget(self, agent_name: str, amount: Decimal) -> None:
        budget = self.budgets.get(agent_name, X402BudgetConfig(25.0, 5.0))
        if amount > Decimal(str(budget.max_payment_per_request)):
            raise X402PaymentError(
                f"Payment ${amount} exceeds per-request limit ${budget.max_payment_per_request} for {agent_name}"
            )
        today = time.strftime("%Y-%m-%d")
        record = self._daily_spend.get(agent_name)
        if not record or record["date"] != today:
            record = {"date": today, "spent": Decimal("0")}
            self._daily_spend[agent_name] = record
        projected = record["spent"] + amount
        if projected > Decimal(str(budget.daily_limit_usdc)):
            raise X402PaymentError(
                f"Payment would exceed daily limit ${budget.daily_limit_usdc} for {agent_name}"
            )
        record["spent"] = projected

    def _to_decimal(self, value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        try:
            text = str(value).replace("USDC", "").replace("$", "").strip()
            return Decimal(text)
        except (InvalidOperation, TypeError):
            return Decimal("0")

    def _release_budget_hold(self, agent_name: str, amount: Decimal) -> None:
        record = self._daily_spend.get(agent_name)
        if not record:
            return
        record["spent"] = max(Decimal("0"), record["spent"] - amount)

    # ------------------------------------------------------------------ #
    # Public staged-payment helpers
    # ------------------------------------------------------------------ #

    def authorize_payment(
        self,
        *,
        agent_name: str,
        vendor: str,
        amount: float,
        metadata: Optional[Dict[str, Any]] = None,
        token: str = "USDC",
        chain: str = "base",
    ) -> str:
        """Reserve funds for a deployment/service that will be captured later."""
        metadata = dict(metadata or {})
        challenge = PaymentChallenge(
            amount=self._to_decimal(amount),
            token=token.upper(),
            chain=chain.lower(),
            recipient=self.wallet_address or metadata.get("recipient", "authorization"),
            vendor=vendor,
            url=metadata.get("url", vendor),
        )
        self._require_approval(
            agent_name=agent_name,
            vendor=vendor,
            amount=challenge.amount,
            metadata=metadata,
        )
        self._enforce_budget(agent_name, challenge.amount)
        auth_id = f"auth_{uuid.uuid4()}"
        self._authorizations[auth_id] = {
            "agent": agent_name,
            "challenge": challenge,
            "metadata": metadata,
        }
        self._record_transaction(
            agent_name=agent_name,
            vendor=vendor,
            challenge=challenge,
            receipt=None,
            metadata=metadata,
            mode="authorized",
            success=True,
            authorization_id=auth_id,
        )
        return auth_id

    def capture_payment(
        self,
        authorization_id: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentReceipt:
        """Complete a previously authorized payment."""
        if authorization_id not in self._authorizations:
            raise ValueError(f"Unknown authorization: {authorization_id}")
        record = self._authorizations.pop(authorization_id)
        challenge: PaymentChallenge = record["challenge"]
        agent_name: str = record["agent"]
        merged_metadata = {**record.get("metadata", {}), **(metadata or {})}
        try:
            receipt = self._sign_payment(
                agent_name,
                challenge,
                merged_metadata,
                enforce_budget=False,
            )
        except Exception:
            # Put authorization back so callers can retry or cancel
            self._authorizations[authorization_id] = record
            raise
        self._record_transaction(
            agent_name=agent_name,
            vendor=challenge.vendor,
            challenge=challenge,
            receipt=receipt,
            metadata=merged_metadata,
            mode="capture",
            success=True,
            authorization_id=authorization_id,
        )
        return receipt

    def cancel_authorization(
        self,
        authorization_id: str,
        *,
        reason: Optional[str] = None,
    ) -> None:
        """Release reserved funds if a deployment or service fails."""
        record = self._authorizations.pop(authorization_id, None)
        if not record:
            raise ValueError(f"Unknown authorization: {authorization_id}")
        challenge: PaymentChallenge = record["challenge"]
        agent_name: str = record["agent"]
        metadata = dict(record.get("metadata", {}))
        if reason:
            metadata["cancel_reason"] = reason
        self._release_budget_hold(agent_name, challenge.amount)
        self._record_transaction(
            agent_name=agent_name,
            vendor=challenge.vendor,
            challenge=challenge,
            receipt=None,
            metadata=metadata,
            mode="authorization_cancelled",
            success=False,
            authorization_id=authorization_id,
        )

_singleton: Optional[X402Client] = None


def get_x402_client() -> X402Client:
    """Shared singleton so agents can reuse budgets/ledger."""
    global _singleton  # pylint: disable=global-statement
    if _singleton is None:
        _singleton = X402Client()
    return _singleton

