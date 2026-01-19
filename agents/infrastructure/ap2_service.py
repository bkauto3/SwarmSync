"""
AP2 Service Layer
=================

Provides a shared wrapper on the AP2 connector to standardize budgets, thresholds,
and telemetry. Agents call this service instead of interacting with AP2Connector
directly so all budgets, alerts, and dashboard events stay centralized.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from infrastructure.ap2_connector import (
    AP2Connector,
    CartItem,
    AP2IntentMandate,
)
from infrastructure.ap2_batch_approval import AP2BatchApprovalManager
from infrastructure.ap2_circuit_breaker import AP2CircuitRegistry, CircuitState
from infrastructure.business_monitor import get_monitor


@dataclass
class AP2BudgetConfig:
    monthly_limit: float
    per_transaction_alert: float
    require_manual_above: float


DEFAULT_BUDGETS: Dict[str, AP2BudgetConfig] = {
    "marketing_agent": AP2BudgetConfig(monthly_limit=5000, per_transaction_alert=1000, require_manual_above=5000),
    "deploy_agent": AP2BudgetConfig(monthly_limit=1000, per_transaction_alert=200, require_manual_above=500),
    "genesis_meta_agent": AP2BudgetConfig(monthly_limit=5000, per_transaction_alert=500, require_manual_above=1000),
    "content_agent": AP2BudgetConfig(monthly_limit=500, per_transaction_alert=100, require_manual_above=100),
    "support_agent": AP2BudgetConfig(monthly_limit=800, per_transaction_alert=100, require_manual_above=150),
    "pricing_agent": AP2BudgetConfig(monthly_limit=1500, per_transaction_alert=300, require_manual_above=500),
    "finance_agent": AP2BudgetConfig(monthly_limit=15000, per_transaction_alert=2500, require_manual_above=5000),
    "commerce_agent": AP2BudgetConfig(monthly_limit=3000, per_transaction_alert=400, require_manual_above=600),
    "seo_agent": AP2BudgetConfig(monthly_limit=500, per_transaction_alert=100, require_manual_above=200),
    "email_agent": AP2BudgetConfig(monthly_limit=200, per_transaction_alert=50, require_manual_above=200),
    "analyst_agent": AP2BudgetConfig(monthly_limit=500, per_transaction_alert=100, require_manual_above=200),
}


class AP2Service:
    def __init__(
        self,
        connector: Optional[AP2Connector] = None,
        budgets: Optional[Dict[str, AP2BudgetConfig]] = None
    ):
        self.connector = connector or AP2Connector()
        self.budgets = budgets or DEFAULT_BUDGETS
        self.intent_cache: Dict[str, AP2IntentMandate] = {}
        self.auto_approve = os.getenv("AP2_AUTO_APPROVE", "false").lower() == "true"
        self.auto_approve_limit = float(os.getenv("AP2_AUTO_APPROVE_LIMIT", "100.0"))
        enable_batch = os.getenv("AP2_ENABLE_BATCH_APPROVAL", "true").lower() == "true"
        self.batch_manager = AP2BatchApprovalManager(budgets=self.budgets) if enable_batch else None
        self.circuit_registry = AP2CircuitRegistry()
        self.global_disabled = os.getenv("AP2_DISABLE_ALL", "false").lower() in {"1", "true", "yes"}
        try:
            self.monitor = get_monitor()
        except Exception:
            self.monitor = None
        if self.monitor:
            try:
                self.monitor.register_ap2_budgets(self.budgets)
            except Exception:
                pass

    def _get_budget(self, agent_name: str) -> AP2BudgetConfig:
        return self.budgets.get(agent_name, AP2BudgetConfig(500.0, 100.0, 250.0))

    def _is_agent_enabled(self, agent_name: str) -> bool:
        if self.global_disabled:
            return False
        flag_key = f"ENABLE_AP2_{agent_name.upper()}"
        return os.getenv(flag_key, "true").lower() in {"1", "true", "yes"}

    async def create_intent(
        self,
        agent_name: str,
        user_id: str,
        task_description: str,
        max_budget: Optional[float] = None,
        categories: Optional[List[str]] = None
    ) -> AP2IntentMandate:
        budget = self._get_budget(agent_name)
        max_price = max_budget or budget.monthly_limit
        intent = await self.connector.create_intent_mandate(
            user_id=user_id,
            agent_id=agent_name,
            task_description=task_description,
            max_price_cents=int(max_price * 100),
            currency="USD",
            valid_for_hours=720,
            allowed_categories=categories or [],
            require_approval=True
        )
        self.intent_cache[agent_name] = intent
        self._record_event(agent_name, "intent_created", "pending", max_price)
        return intent

    async def request_purchase(
        self,
        agent_name: str,
        user_id: str,
        service_name: str,
        price: float,
        categories: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if price <= 0:
            raise ValueError("Price must be positive")
        if not self._is_agent_enabled(agent_name):
            raise RuntimeError(f"AP2 disabled for {agent_name}.")

        batch_decision = None
        breaker = self.circuit_registry.get(agent_name)
        if not breaker.allow():
            raise RuntimeError(f"AP2 circuit breaker OPEN for {agent_name}.")
        if self.batch_manager:
            batch_decision = self.batch_manager.evaluate_purchase(agent_name, user_id, price)
            if batch_decision.blocked:
                raise ValueError(
                    f"{agent_name} batch mandate exhausted for user {user_id}. "
                    "Request additional budget before continuing."
                )

        budget = self._get_budget(agent_name)
        if price > budget.monthly_limit:
            raise ValueError(f"Requested price ${price} exceeds monthly limit ${budget.monthly_limit}")

        intent = await self.create_intent(
            agent_name=agent_name,
            user_id=user_id,
            task_description=f"{agent_name} purchase: {service_name}",
            max_budget=budget.monthly_limit,
            categories=categories
        )

        cart_item = CartItem(
            item_id=f"{agent_name}_{service_name}_{int(datetime.now(timezone.utc).timestamp())}",
            name=f"{service_name}",
            quantity=1,
            unit_price_cents=int(price * 100),
            currency="USD"
        )
        cart = await self.connector.create_cart_mandate(
            intent_mandate_id=intent.mandate_id,
            items=[cart_item],
            user_id=user_id
        )

        approval_status = "pending"
        if self.auto_approve and price <= self.auto_approve_limit:
            await self.connector.approve_cart_mandate(cart.mandate_id, user_id)
            approval_status = "approved"

        if self.batch_manager:
            self.batch_manager.record_purchase(agent_name, user_id, price)

        extra_meta = dict(metadata or {})
        if batch_decision:
            extra_meta["batch_approval"] = batch_decision.to_dict()
            if batch_decision.warning_triggered:
                extra_meta.setdefault("alerts", []).append("batch_budget_warning")
        self._record_event(agent_name, "cart_created", approval_status, price, extra_meta)

        breaker.record_success()

        result = {
            "intent": intent.to_dict(),
            "cart": cart.to_dict(),
            "status": approval_status,
            "price": price,
        }
        if batch_decision:
            result["batch_approval"] = batch_decision.to_dict()
        return result

    async def safe_request_purchase(self, *args, **kwargs) -> Dict[str, Any]:
        """Wrapper that records circuit failure expectations."""
        agent_name = kwargs.get("agent_name", "unknown_agent")
        breaker = self.circuit_registry.get(agent_name)
        try:
            return await self.request_purchase(*args, **kwargs)
        except Exception:
            breaker.record_failure()
            raise

    def _record_event(
        self,
        agent_name: str,
        event_type: str,
        status: str,
        cost: float,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        if not self.monitor:
            return
        payload = {
            "event_type": event_type,
            "status": status,
            "cost": cost,
            "extra": extra or {},
        }
        self.monitor.record_ap2_event(agent_name, payload)
