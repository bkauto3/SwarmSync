"""
Pricing Agent - AP2-integrated pricing insights + experimentation pipeline.

Handles dataset purchases, elasticity experiments, pricing deployment, and reporting
while enforcing AP2 budgets/signatures for every paid tool.
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
from pathlib import Path
from typing import Any, Awaitable, Dict, Optional

from infrastructure.ap2_service import AP2Service, AP2BudgetConfig, DEFAULT_BUDGETS
from infrastructure.x402_vendor_cache import get_x402_vendor_cache
from infrastructure.x402_client import get_x402_client, X402PaymentError

logger = logging.getLogger(__name__)


class PricingAgent:
    """Pricing experimentation and insights agent with AP2 coverage."""

    def __init__(self, business_id: str = "default"):
        self.business_id = business_id
        self.ap2_service: Optional[AP2Service] = None
        self._ap2_loop: Optional[asyncio.AbstractEventLoop] = None
        self._ap2_thread: Optional[threading.Thread] = None
        self._budget_config = self._get_pricing_budget()
        self._monthly_spend = 0.0
        self._budget_window = datetime.utcnow().strftime("%Y-%m")
        self._ap2_secret = os.getenv("AP2_SECRET_KEY", "dev-pricing-secret")
        self.pricing_audit: list[Dict[str, Any]] = []
        self.pricing_alerts: list[Dict[str, Any]] = []
        self.vendor_cache = get_x402_vendor_cache()
        self.x402_client = get_x402_client()
        self.experiment_log_path = Path(os.getenv("PRICING_EXPERIMENT_LOG", "data/pricing/experiments.jsonl"))
        self.experiment_log_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self.ap2_service = AP2Service()
        except (RuntimeError, OSError) as exc:
            logger.warning("PricingAgent AP2 unavailable: %s", exc)
            self.ap2_service = None

        if self.ap2_service:
            self._ap2_loop = asyncio.new_event_loop()
            self._ap2_thread = threading.Thread(
                target=self._run_ap2_loop,
                name="PricingAgent-AP2Loop",
                daemon=True,
            )
            self._ap2_thread.start()

    # ------------------------------------------------------------------ #
    # Public methods
    # ------------------------------------------------------------------ #
    def purchase_dataset(self, provider: str, price: float, records: int) -> str:
        receipt = self._ensure_pricing_budget(
            service_name=f"{provider} dataset",
            amount=price,
            metadata={"records": records, "category": "datasets"},
        )
        x402_receipt = self._charge_x402(
            vendor="pricing-dataset-api",
            amount=max(0.05, price * 0.001),
            metadata={"provider": provider, "records": records},
        )
        result = {
            "provider": provider,
            "records": records,
            "price": price,
            "purchased_at": datetime.utcnow().isoformat(),
            "ap2_approval": receipt,
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def run_elasticity_experiment(
        self,
        experiment_id: str,
        cloud_hours: float,
        hourly_rate: float = 12.0,
        expected_uplift_pct: float = 3.0,
    ) -> str:
        spend = round(cloud_hours * hourly_rate, 2)
        receipt = self._ensure_pricing_budget(
            service_name="Elasticity compute cluster",
            amount=spend,
            metadata={"experiment_id": experiment_id, "hours": cloud_hours},
        )
        x402_receipt = self._charge_x402(
            vendor="pricing-elasticity-compute",
            amount=max(0.08, spend * 0.002),
            metadata={"experiment_id": experiment_id, "hours": cloud_hours},
        )
        result = {
            "experiment_id": experiment_id,
            "cloud_hours": cloud_hours,
            "cost": spend,
            "status": "running",
            "ap2_approval": receipt,
            "x402_payment": x402_receipt,
            "expected_uplift_pct": expected_uplift_pct,
        }
        self._record_experiment_summary(
            experiment_id=experiment_id,
            cost=spend,
            uplift_pct=expected_uplift_pct,
            metadata={"cloud_hours": cloud_hours, "hourly_rate": hourly_rate},
        )
        return json.dumps(result, indent=2)

    def deploy_pricing_update(self, channel: str, spend: float, risk_level: str) -> str:
        receipt = self._ensure_pricing_budget(
            service_name=f"{channel} promotion",
            amount=spend,
            metadata={"channel": channel, "risk": risk_level},
        )
        x402_receipt = self._charge_x402(
            vendor="pricing-deployment",
            amount=max(0.04, spend * 0.0015),
            metadata={"channel": channel, "risk": risk_level},
        )
        result = {
            "channel": channel,
            "spend": spend,
            "risk_level": risk_level,
            "deployed_at": datetime.utcnow().isoformat(),
            "ap2_approval": receipt,
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def generate_pricing_report(
        self,
        period: str,
        dashboards: int,
        seat_cost: float = 35.0,
    ) -> str:
        spend = round(dashboards * seat_cost, 2)
        receipt = self._ensure_pricing_budget(
            service_name="BI seat bundle",
            amount=spend,
            metadata={"dashboards": dashboards, "category": "reporting"},
        )
        x402_receipt = self._charge_x402(
            vendor="pricing-reporting",
            amount=max(0.03, spend * 0.001),
            metadata={"period": period, "dashboards": dashboards},
        )
        result = {
            "period": period,
            "dashboards": dashboards,
            "generated_at": datetime.utcnow().isoformat(),
            "ap2_approval": receipt,
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def run_pricing_cycle(
        self,
        provider: str,
        dataset_price: float,
        records: int,
        cloud_hours: float,
        deployment_spend: float,
    ) -> Dict[str, Any]:
        dataset = json.loads(self.purchase_dataset(provider, dataset_price, records))
        experiment = json.loads(self.run_elasticity_experiment("elasticity-cycle", cloud_hours))
        deployment = json.loads(self.deploy_pricing_update("in-app", deployment_spend, "medium"))
        report = json.loads(self.generate_pricing_report("current_month", dashboards=4))
        receipts = [
            dataset.get("ap2_approval"),
            experiment.get("ap2_approval"),
            deployment.get("ap2_approval"),
            report.get("ap2_approval"),
        ]
        return {
            "dataset": dataset,
            "experiment": experiment,
            "deployment": deployment,
            "report": report,
            "ap2_receipts": [r for r in receipts if r],
        }

    # ------------------------------------------------------------------ #
    # Diagnostics / accessors
    # ------------------------------------------------------------------ #
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
        return list(self.pricing_audit)

    def get_alerts(self) -> list[Dict[str, Any]]:
        return list(self.pricing_alerts)

    def _record_experiment_summary(
        self,
        *,
        experiment_id: str,
        cost: float,
        uplift_pct: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = {
            "experiment_id": experiment_id,
            "cost": cost,
            "expected_uplift_pct": uplift_pct,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        roi = uplift_pct / 100.0
        entry["roi_delta"] = round(roi - (cost / max(cost, 1.0)), 4)
        with self.experiment_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _run_ap2_loop(self) -> None:
        if not self._ap2_loop:
            return
        asyncio.set_event_loop(self._ap2_loop)
        self._ap2_loop.run_forever()

    def _execute_ap2_coro(self, coro: Awaitable[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.ap2_service:
            raise RuntimeError("AP2 service unavailable for PricingAgent.")
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

    def _charge_x402(
        self,
        vendor: str,
        amount: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            prepared_metadata = self._prepare_x402_metadata(vendor, metadata)
            receipt = self.x402_client.record_manual_payment(
                agent_name="pricing_agent",
                vendor=vendor,
                amount=max(amount, 0.01),
                metadata=prepared_metadata,
            )
            return {
                "tx_hash": receipt.tx_hash,
                "amount": float(receipt.amount),
                "token": receipt.token,
                "chain": receipt.chain,
            }
        except X402PaymentError as exc:
            raise RuntimeError(f"Pricing Agent x402 budget exceeded: {exc}") from exc

    def _prepare_x402_metadata(
        self, vendor: str, metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        data = dict(metadata or {})
        data.setdefault("business_id", self.business_id)
        data.setdefault("agent_name", "pricing_agent")
        data.setdefault("category", "pricing")
        capabilities = self.vendor_cache.lookup(vendor)
        if capabilities:
            data.setdefault("accepted_tokens", capabilities.get("accepted_tokens"))
            data.setdefault("preferred_chain", capabilities.get("preferred_chain"))
        return data

    def _get_pricing_budget(self) -> AP2BudgetConfig:
        return DEFAULT_BUDGETS.get(
            "pricing_agent",
            AP2BudgetConfig(monthly_limit=1500.0, per_transaction_alert=300.0, require_manual_above=500.0),
        )

    def _reset_budget_if_needed(self) -> None:
        current_window = datetime.utcnow().strftime("%Y-%m")
        if current_window != self._budget_window:
            self._budget_window = current_window
            self._monthly_spend = 0.0

    def _ensure_pricing_budget(
        self,
        service_name: str,
        amount: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("Pricing spend must be positive.")
        if not self.ap2_service:
            raise RuntimeError("AP2 service unavailable for PricingAgent.")

        self._reset_budget_if_needed()
        if self._monthly_spend + amount > self._budget_config.monthly_limit:
            raise ValueError(
                f"Pricing monthly budget exhausted. Remaining "
                f"${self._budget_config.monthly_limit - self._monthly_spend:.2f}."
            )

        auto_approval = amount <= 75.0
        manual_review = amount > 400.0
        receipt = self._execute_ap2_coro(
            self.ap2_service.request_purchase(
                agent_name="pricing_agent",
                user_id=f"{self.business_id}_pricing",
                service_name=service_name,
                price=amount,
                categories=["pricing"],
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
            raise RuntimeError("PricingAgent AP2 signature verification failed.")

        self._monthly_spend += amount
        self.pricing_audit.append(payload)
        if amount >= self._budget_config.per_transaction_alert:
            self.pricing_alerts.append(
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


__all__ = ["PricingAgent"]

