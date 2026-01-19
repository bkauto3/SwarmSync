"""
Commerce Agent - AP2-backed commerce orchestration.

Manages domain registration, payment gateways, tax engines, and fulfillment budgets
with signatures and alerts.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Awaitable, Dict, Optional

from infrastructure.ap2_service import AP2Service, AP2BudgetConfig, DEFAULT_BUDGETS
from infrastructure.x402_client import get_x402_client, X402PaymentError
from infrastructure.x402_vendor_cache import get_x402_vendor_cache

logger = logging.getLogger(__name__)


class CommerceAgent:
    """Commerce stack automation agent with AP2 cost controls."""

    def __init__(self, business_id: str = "default"):
        self.business_id = business_id
        self.ap2_service: Optional[AP2Service] = None
        self._ap2_loop: Optional[asyncio.AbstractEventLoop] = None
        self._ap2_thread: Optional[threading.Thread] = None
        self._budget_config = self._get_commerce_budget()
        self._monthly_spend = 0.0
        self._budget_window = datetime.utcnow().strftime("%Y-%m")
        self._ap2_secret = os.getenv("AP2_SECRET_KEY", "dev-commerce-secret")
        self.commerce_audit: list[Dict[str, Any]] = []
        self.commerce_alerts: list[Dict[str, Any]] = []
        self.x402_client = get_x402_client()
        self.vendor_cache = get_x402_vendor_cache()

        try:
            self.ap2_service = AP2Service()
        except (RuntimeError, OSError) as exc:
            logger.warning("CommerceAgent AP2 unavailable: %s", exc)
            self.ap2_service = None

        if self.ap2_service:
            self._ap2_loop = asyncio.new_event_loop()
            self._ap2_thread = threading.Thread(
                target=self._run_ap2_loop,
                name="CommerceAgent-AP2Loop",
                daemon=True,
            )
            self._ap2_thread.start()

    def _charge_x402(self, vendor: str, amount: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        try:
            prepared_metadata = self._prepare_x402_metadata(vendor, metadata)
            self.x402_client.record_manual_payment(
                agent_name="commerce_agent",
                vendor=vendor,
                amount=max(amount, 0.01),
                metadata=prepared_metadata,
            )
        except X402PaymentError as exc:
            raise RuntimeError(f"Commerce Agent x402 budget exceeded: {exc}") from exc

    def _prepare_x402_metadata(
        self, vendor: str, metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        data = dict(metadata or {})
        data.setdefault("business_id", self.business_id)
        data.setdefault("agent_name", "commerce_agent")
        data.setdefault("category", "commerce")
        capabilities = self.vendor_cache.lookup(vendor)
        if capabilities:
            data.setdefault("accepted_tokens", capabilities.get("accepted_tokens"))
            data.setdefault("preferred_chain", capabilities.get("preferred_chain"))
        return data

    def register_domain(self, domain: str, registrar: str = "Namecheap", registration_cost: float = 12.0) -> str:
        receipt = self._ensure_commerce_budget(
            service_name=f"{registrar} domain",
            amount=registration_cost,
            metadata={"domain": domain},
        )
        staged_amount = max(0.02, registration_cost * 0.01)
        auth_id = self._authorize_staged_payment(
            vendor="commerce-domain-api",
            amount=staged_amount,
            metadata={"domain": domain, "registrar": registrar},
        )
        result = {
            "domain": domain,
            "registrar": registrar,
            "cost": registration_cost,
            "status": "registered",
            "ap2_approval": receipt,
        }
        try:
            if auth_id:
                self._capture_staged_payment(auth_id, {"domain": domain, "status": "registered"})
        except Exception as exc:
            self._cancel_staged_payment(auth_id, f"domain_capture_failed:{exc}")
        return json.dumps(result, indent=2)
        return json.dumps(result, indent=2)

    def activate_payment_gateway(self, gateway: str, setup_fee: float) -> str:
        receipt = self._ensure_commerce_budget(
            service_name=f"{gateway} gateway setup",
            amount=setup_fee,
            metadata={"gateway": gateway},
        )
        staged_amount = max(0.03, setup_fee * 0.005)
        auth_id = self._authorize_staged_payment(
            vendor="commerce-gateway-cert",
            amount=staged_amount,
            metadata={"gateway": gateway},
        )
        result = {
            "gateway": gateway,
            "setup_fee": setup_fee,
            "activated_at": datetime.utcnow().isoformat(),
            "ap2_approval": receipt,
        }
        try:
            if auth_id:
                self._capture_staged_payment(auth_id, {"gateway": gateway, "status": "activated"})
        except Exception as exc:
            self._cancel_staged_payment(auth_id, f"gateway_capture_failed:{exc}")
        return json.dumps(result, indent=2)

    def configure_tax_engine(self, provider: str, monthly_cost: float) -> str:
        receipt = self._ensure_commerce_budget(
            service_name=f"{provider} tax engine",
            amount=monthly_cost,
            metadata={"provider": provider},
        )
        result = {
            "provider": provider,
            "monthly_cost": monthly_cost,
            "configured_at": datetime.utcnow().isoformat(),
            "ap2_approval": receipt,
        }
        return json.dumps(result, indent=2)

    def ship_fulfillment_batch(self, carrier: str, orders: int, per_order_cost: float) -> str:
        spend = round(orders * per_order_cost, 2)
        receipt = self._ensure_commerce_budget(
            service_name=f"{carrier} fulfillment batch",
            amount=spend,
            metadata={"orders": orders},
        )
        result = {
            "carrier": carrier,
            "orders": orders,
            "total_cost": spend,
            "ap2_approval": receipt,
        }
        return json.dumps(result, indent=2)

    def launch_commerce_stack(
        self,
        domain: str,
        registrar_cost: float,
        gateway_fee: float,
        tax_engine_cost: float,
        fulfillment_orders: int,
    ) -> Dict[str, Any]:
        domain_receipt = json.loads(self.register_domain(domain, registration_cost=registrar_cost))
        gateway = json.loads(self.activate_payment_gateway("Stripe", gateway_fee))
        tax = json.loads(self.configure_tax_engine("Avalara", tax_engine_cost))
        fulfillment = json.loads(self.ship_fulfillment_batch("Shippo", fulfillment_orders, per_order_cost=8.5))
        receipts = [
            domain_receipt.get("ap2_approval"),
            gateway.get("ap2_approval"),
            tax.get("ap2_approval"),
            fulfillment.get("ap2_approval"),
        ]
        return {
            "domain": domain_receipt,
            "gateway": gateway,
            "tax": tax,
            "fulfillment": fulfillment,
            "ap2_receipts": [r for r in receipts if r],
        }

    def shutdown(self) -> None:
        if self._ap2_loop:
            self._ap2_loop.call_soon_threadsafe(self._ap2_loop.stop)
        if self._ap2_thread:
            self._ap2_thread.join(timeout=1)
        self._ap2_loop = None
        self._ap2_thread = None

    def get_budget_metrics(self) -> Dict[str, Any]:
        self._reset_budget_if_needed()
        return {
            "monthly_limit": self._budget_config.monthly_limit,
            "monthly_spend": self._monthly_spend,
            "remaining_budget": max(self._budget_config.monthly_limit - self._monthly_spend, 0),
            "window": self._budget_window,
        }

    def get_audit_log(self) -> list[Dict[str, Any]]:
        return list(self.commerce_audit)

    def get_alerts(self) -> list[Dict[str, Any]]:
        return list(self.commerce_alerts)

    def _authorize_staged_payment(
        self, *, vendor: str, amount: float, metadata: Dict[str, Any]
    ) -> Optional[str]:
        if not self.x402_client:
            return None
        try:
            return self.x402_client.authorize_payment(
                agent_name="commerce_agent",
                vendor=vendor,
                amount=amount,
                metadata=metadata,
            )
        except X402PaymentError as exc:
            raise RuntimeError(f"Commerce Agent staged payment denied: {exc}") from exc
        except Exception as exc:
            logger.warning("CommerceAgent: staged payment skipped (%s)", exc)
            return None

    def _capture_staged_payment(self, auth_id: Optional[str], metadata: Dict[str, Any]) -> None:
        if auth_id and self.x402_client:
            self.x402_client.capture_payment(auth_id, metadata=metadata)

    def _cancel_staged_payment(self, auth_id: Optional[str], reason: str) -> None:
        if not auth_id or not self.x402_client:
            return
        try:
            self.x402_client.cancel_authorization(auth_id, reason=reason)
        except Exception as exc:
            logger.warning("CommerceAgent: failed to cancel authorization %s (%s)", auth_id, exc)

    def _run_ap2_loop(self) -> None:
        if not self._ap2_loop:
            return
        asyncio.set_event_loop(self._ap2_loop)
        self._ap2_loop.run_forever()

    def _execute_ap2_coro(self, coro: Awaitable[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.ap2_service:
            raise RuntimeError("AP2 service unavailable for CommerceAgent.")
        if self._ap2_loop:
            future = asyncio.run_coroutine_threadsafe(coro, self._ap2_loop)
            try:
                result = future.result(timeout=30)
            except asyncio.TimeoutError as exc:
                raise RuntimeError("AP2 request timed out") from exc
        else:
            result = asyncio.run(coro)
        if result.get("status") != "approved":
            raise RuntimeError(f"AP2 request denied: {result.get('status')}")
        return result

    def _get_commerce_budget(self) -> AP2BudgetConfig:
        return DEFAULT_BUDGETS.get(
            "commerce_agent",
            AP2BudgetConfig(monthly_limit=3000.0, per_transaction_alert=400.0, require_manual_above=600.0),
        )

    def _reset_budget_if_needed(self) -> None:
        current_window = datetime.utcnow().strftime("%Y-%m")
        if current_window != self._budget_window:
            self._budget_window = current_window
            self._monthly_spend = 0.0

    def _ensure_commerce_budget(
        self,
        service_name: str,
        amount: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("Commerce spend must be positive.")
        if not self.ap2_service:
            raise RuntimeError("AP2 service unavailable for CommerceAgent.")

        self._reset_budget_if_needed()
        if self._monthly_spend + amount > self._budget_config.monthly_limit:
            raise ValueError(
                f"Commerce monthly budget exhausted. Remaining "
                f"${self._budget_config.monthly_limit - self._monthly_spend:.2f}."
            )

        auto_approval = amount <= 60.0
        manual_review = amount > 500.0
        receipt = self._execute_ap2_coro(
            self.ap2_service.request_purchase(
                agent_name="commerce_agent",
                user_id=f"{self.business_id}_commerce",
                service_name=service_name,
                price=amount,
                categories=["commerce"],
                metadata=metadata or {},
            )
        )
        payload = {
            **receipt,
            "service": service_name,
            "amount": amount,
            "auto_approval": auto_approval,
            "manual_review": manual_review,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        signature = self._sign_payload(payload)
        payload["signature"] = signature
        if not self._verify_signature(payload, signature):
            raise RuntimeError("CommerceAgent AP2 signature verification failed.")

        self._monthly_spend += amount
        self.commerce_audit.append(payload)
        if amount >= self._budget_config.per_transaction_alert:
            self.commerce_alerts.append(
                {"service": service_name, "amount": amount, "timestamp": payload["timestamp"]}
            )
        return payload

    def _sign_payload(self, payload: Dict[str, Any]) -> str:
        body = json.dumps(payload, sort_keys=True)
        return hmac.new(
            self._ap2_secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _verify_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        comparison = {k: v for k, v in payload.items() if k != "signature"}
        expected = self._sign_payload(comparison)
        return hmac.compare_digest(signature, expected)


__all__ = ["CommerceAgent"]

