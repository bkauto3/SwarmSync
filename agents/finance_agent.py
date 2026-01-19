"""
Finance Agent - AP2-governed treasury + accounting workflows.

Provides payroll, vendor payments, bank reconciliation, and close reporting with
budget enforcement, alerts, and signed audit trails.
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
from typing import Any, Awaitable, Dict, Optional, List

from infrastructure.ap2_service import AP2Service, AP2BudgetConfig, DEFAULT_BUDGETS
from infrastructure.x402_vendor_cache import get_x402_vendor_cache
from infrastructure.x402_client import get_x402_client, X402PaymentError

logger = logging.getLogger(__name__)


class FinanceAgent:
    """Finance operations agent with AP2 approvals."""

    def __init__(self, business_id: str = "default"):
        self.business_id = business_id
        self.ap2_service: Optional[AP2Service] = None
        self._ap2_loop: Optional[asyncio.AbstractEventLoop] = None
        self._ap2_thread: Optional[threading.Thread] = None
        self._budget_config = self._get_finance_budget()
        self._monthly_spend = 0.0
        self._budget_window = datetime.utcnow().strftime("%Y-%m")
        self._ap2_secret = os.getenv("AP2_SECRET_KEY", "dev-finance-secret")
        self.finance_audit: list[Dict[str, Any]] = []
        self.finance_alerts: list[Dict[str, Any]] = []
        self.vendor_cache = get_x402_vendor_cache()
        self.x402_client = get_x402_client()

        try:
            self.ap2_service = AP2Service()
        except (RuntimeError, OSError) as exc:
            logger.warning("FinanceAgent AP2 unavailable: %s", exc)
            self.ap2_service = None

        if self.ap2_service:
            self._ap2_loop = asyncio.new_event_loop()
            self._ap2_thread = threading.Thread(
                target=self._run_ap2_loop,
                name="FinanceAgent-AP2Loop",
                daemon=True,
            )
            self._ap2_thread.start()

    def run_payroll_batch(self, employee_count: int, cost_per_employee: float) -> str:
        total = round(employee_count * cost_per_employee, 2)
        receipt = self._ensure_finance_budget(
            service_name="Payroll processor",
            amount=total,
            metadata={"employees": employee_count},
        )
        x402_receipt = self._charge_x402(
            vendor="finance-payroll-api",
            amount=max(0.05, total * 0.0005),
            metadata={"employees": employee_count},
        )
        result = {
            "employee_count": employee_count,
            "total_cost": total,
            "processed_at": datetime.utcnow().isoformat(),
            "ap2_approval": receipt,
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def process_vendor_invoice(self, vendor: str, amount: float, category: str) -> str:
        receipt = self._ensure_finance_budget(
            service_name=f"{vendor} invoice",
            amount=amount,
            metadata={"category": category},
        )
        x402_receipt = self._charge_x402(
            vendor="finance-vendor-ledger",
            amount=max(0.03, amount * 0.0002),
            metadata={"vendor": vendor, "category": category},
        )
        result = {
            "vendor": vendor,
            "amount": amount,
            "category": category,
            "status": "scheduled",
            "ap2_approval": receipt,
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def sync_bank_fees(self, account: str, fee_amount: float) -> str:
        receipt = self._ensure_finance_budget(
            service_name="Bank fee reconciliation",
            amount=fee_amount,
            metadata={"account": account},
        )
        x402_receipt = self._charge_x402(
            vendor="finance-bank-sync",
            amount=max(0.02, fee_amount * 0.001),
            metadata={"account": account},
        )
        result = {
            "account": account,
            "fee_amount": fee_amount,
            "synced_at": datetime.utcnow().isoformat(),
            "ap2_approval": receipt,
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def generate_finance_report(self, month: str, tooling_cost: float = 150.0) -> str:
        receipt = self._ensure_finance_budget(
            service_name="Accounting analytics",
            amount=tooling_cost,
            metadata={"month": month},
        )
        x402_receipt = self._charge_x402(
            vendor="finance-reporting",
            amount=max(0.03, tooling_cost * 0.001),
            metadata={"month": month},
        )
        result = {
            "month": month,
            "generated_at": datetime.utcnow().isoformat(),
            "ap2_approval": receipt,
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def run_finance_close(
        self,
        employee_count: int,
        cost_per_employee: float,
        vendor_amount: float,
        category: str,
        bank_fee: float,
    ) -> Dict[str, Any]:
        payroll = json.loads(self.run_payroll_batch(employee_count, cost_per_employee))
        vendor = json.loads(self.process_vendor_invoice("Core SaaS", vendor_amount, category))
        fees = json.loads(self.sync_bank_fees("operating", bank_fee))
        report = json.loads(self.generate_finance_report(datetime.utcnow().strftime("%Y-%m")))
        receipts = [
            payroll.get("ap2_approval"),
            vendor.get("ap2_approval"),
            fees.get("ap2_approval"),
            report.get("ap2_approval"),
        ]
        return {
            "payroll": payroll,
            "vendor": vendor,
            "fees": fees,
            "report": report,
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
        return list(self.finance_audit)

    def get_alerts(self) -> list[Dict[str, Any]]:
        return list(self.finance_alerts)

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
            raise RuntimeError("AP2 service unavailable for FinanceAgent.")
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
                agent_name="finance_agent",
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
            raise RuntimeError(f"Finance Agent x402 budget exceeded: {exc}") from exc

    def _prepare_x402_metadata(
        self, vendor: str, metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        data = dict(metadata or {})
        data.setdefault("business_id", self.business_id)
        data.setdefault("agent_name", "finance_agent")
        data.setdefault("category", "finance")
        capabilities = self.vendor_cache.lookup(vendor)
        if capabilities:
            data.setdefault("accepted_tokens", capabilities.get("accepted_tokens"))
            data.setdefault("preferred_chain", capabilities.get("preferred_chain"))
        return data

    def import_x402_transactions(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sync ledger data into the finance audit trail."""
        synced = 0
        for tx in transactions:
            entry = {
                "timestamp": tx.get("timestamp"),
                "vendor": tx.get("vendor"),
                "amount": tx.get("amount_usdc"),
                "agent": tx.get("agent"),
                "metadata": tx.get("metadata", {}),
            }
            self.finance_audit.append(entry)
            synced += 1
        return {"synced": synced, "total_records": len(transactions)}

    def _get_finance_budget(self) -> AP2BudgetConfig:
        return DEFAULT_BUDGETS.get(
            "finance_agent",
            AP2BudgetConfig(monthly_limit=15000.0, per_transaction_alert=2500.0, require_manual_above=5000.0),
        )

    def _reset_budget_if_needed(self) -> None:
        current_window = datetime.utcnow().strftime("%Y-%m")
        if current_window != self._budget_window:
            self._budget_window = current_window
            self._monthly_spend = 0.0

    def _ensure_finance_budget(
        self,
        service_name: str,
        amount: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("Finance spend must be positive.")
        if not self.ap2_service:
            raise RuntimeError("AP2 service unavailable for FinanceAgent.")

        self._reset_budget_if_needed()
        if self._monthly_spend + amount > self._budget_config.monthly_limit:
            raise ValueError(
                f"Finance monthly budget exhausted. Remaining "
                f"${self._budget_config.monthly_limit - self._monthly_spend:.2f}."
            )

        auto_approval = amount <= 200.0
        manual_review = amount > 3000.0
        receipt = self._execute_ap2_coro(
            self.ap2_service.request_purchase(
                agent_name="finance_agent",
                user_id=f"{self.business_id}_finance",
                service_name=service_name,
                price=amount,
                categories=["finance"],
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
            raise RuntimeError("FinanceAgent AP2 signature verification failed.")

        self._monthly_spend += amount
        self.finance_audit.append(payload)
        if amount >= self._budget_config.per_transaction_alert:
            self.finance_alerts.append(
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


__all__ = ["FinanceAgent"]

