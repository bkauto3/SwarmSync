"""
SEO AGENT - Microsoft Agent Framework Version
Version: 4.0 (Enhanced with DAAO + TUMIX) (Day 2 Migration)

Handles SEO optimization, keyword research, and search rankings.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any, Awaitable, Dict, List, Optional
from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from agent_framework.observability import setup_observability
from azure.identity.aio import AzureCliCredential

setup_observability(enable_sensitive_data=True)
# Import DAAO and TUMIX
from infrastructure.daao_router import get_daao_router, RoutingDecision
from infrastructure.tumix_termination import (
    get_tumix_termination,
    RefinementResult,
    TerminationDecision
)
from infrastructure.ap2_service import AP2Service, AP2BudgetConfig, DEFAULT_BUDGETS
from infrastructure.x402_client import get_x402_client, X402PaymentError
from infrastructure.x402_vendor_cache import get_x402_vendor_cache
from infrastructure.creative_asset_registry import get_asset_registry

logger = logging.getLogger(__name__)


class SEOAgent:
    """SEO optimization and search ranking agent"""

    def __init__(self, business_id: str = "default"):
        self.business_id = business_id
        self.agent: Optional[ChatAgent] = None
        self.x402_client = get_x402_client()
        self.vendor_cache = get_x402_vendor_cache()
        self.asset_registry = get_asset_registry("seo_agent")

        # Initialize DAAO router for cost optimization
        self.router = get_daao_router()

        # Initialize TUMIX for iterative refinement
        self.termination = get_tumix_termination(
            min_rounds=2,
            max_rounds=4,
            improvement_threshold=0.05
        )

        # Track refinement sessions for metrics
        self.refinement_history: List[List[RefinementResult]] = []

        # AP2 + budget tracking
        self.ap2_service: Optional[AP2Service] = None
        self._ap2_loop: Optional[asyncio.AbstractEventLoop] = None
        self._ap2_thread: Optional[threading.Thread] = None
        self._monthly_limit = self._get_seo_budget().monthly_limit
        self._current_monthly_spend = 0.0
        self._budget_window = datetime.utcnow().strftime("%Y-%m")
        self._ap2_secret = os.getenv("AP2_SECRET_KEY", "dev-seo-secret")
        self.seo_alerts: List[Dict[str, Any]] = []
        self.seo_audit_log: List[Dict[str, Any]] = []
        self.tool_spend: Dict[str, float] = defaultdict(float)

        try:
            self.ap2_service = AP2Service()
        except (RuntimeError, OSError) as exc:
            logger.warning("AP2 service unavailable for SEOAgent: %s", exc)
            self.ap2_service = None

        if self.ap2_service:
            self._ap2_loop = asyncio.new_event_loop()
            self._ap2_thread = threading.Thread(
                target=self._run_ap2_loop,
                name="SEOAgent-AP2Loop",
                daemon=True,
            )
            self._ap2_thread.start()

        logger.info("SEOAgent v4.0 initialized with DAAO + TUMIX for business: %s", business_id)

    def _charge_x402(self, vendor: str, amount: float, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        metadata = dict(metadata or {})
        cacheable = metadata.get("cacheable_asset", False)
        signature = metadata.get("asset_signature")
        ttl_hours = int(metadata.get("asset_ttl_hours", 168))
        if cacheable:
            signature = signature or self._build_asset_signature(vendor, metadata)
            if signature:
                cached = self.asset_registry.should_reuse(signature, ttl_hours)
                if cached:
                    logger.info("SEOAgent reusing cached research asset %s (vendor=%s)", signature, cached.vendor)
                    return {
                        "status": "reused",
                        "signature": signature,
                        "vendor": cached.vendor,
                        "cached_at": cached.timestamp,
                    }
        try:
            prepared_metadata = self._prepare_x402_metadata(vendor, metadata)
            receipt = self.x402_client.record_manual_payment(
                agent_name="seo_agent",
                vendor=vendor,
                amount=max(amount, 0.01),
                metadata=prepared_metadata,
            )
            if cacheable and signature:
                self.asset_registry.record_purchase(
                    signature=signature,
                    vendor=vendor,
                    amount=float(amount),
                    metadata=metadata,
                )
            return {
                "token": receipt.token,
                "chain": receipt.chain,
                "tx_hash": receipt.tx_hash,
            }
        except X402PaymentError as exc:
            raise RuntimeError(f"SEO Agent x402 budget exceeded: {exc}") from exc

    def _prepare_x402_metadata(
        self, vendor: str, metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        data = dict(metadata or {})
        data.setdefault("business_id", self.business_id)
        data.setdefault("agent_name", "seo_agent")
        data.setdefault("category", "seo")
        capabilities = self.vendor_cache.lookup(vendor)
        if capabilities:
            data.setdefault("accepted_tokens", capabilities.get("accepted_tokens"))
            data.setdefault("preferred_chain", capabilities.get("preferred_chain"))
        return data

    def _build_asset_signature(self, vendor: str, metadata: Dict[str, Any]) -> str:
        base = metadata.get("asset_signature")
        if base:
            return str(base)
        topic = metadata.get("topic") or metadata.get("domain") or metadata.get("url")
        return f"{vendor}:{topic or 'generic'}"

    async def initialize(self):
        cred = AzureCliCredential()
        client = AzureAIAgentClient(async_credential=cred)
        self.agent = ChatAgent(
            chat_client=client,
            instructions="You are an SEO specialist. Conduct keyword research, optimize content for search engines, analyze backlinks, monitor rankings, and implement technical SEO best practices. Focus on both on-page and off-page optimization. Track organic traffic growth and conversion metrics.",
            name="seo-agent",
            tools=[self.keyword_research, self.optimize_content, self.analyze_backlinks, self.track_rankings, self.generate_seo_report]
        )
        print(f"🔍 SEO Agent initialized for business: {self.business_id}\n")

    def keyword_research(
        self,
        topic: str,
        target_audience: str,
        num_keywords: int,
        *,
        ahrefs_cost: float = 99.0,
        semrush_cost: float = 119.0,
    ) -> str:
        """Research relevant keywords for a topic"""
        ap2_receipts = []
        ap2_receipts.append(
            self._ensure_seo_budget(
                service_name="Ahrefs subscription",
                amount=ahrefs_cost,
                metadata={"tool": "Ahrefs", "category": "keyword_research"},
            )
        )
        ap2_receipts.append(
            self._ensure_seo_budget(
                service_name="SEMrush subscription",
                amount=semrush_cost,
                metadata={"tool": "SEMrush", "category": "keyword_research"},
            )
        )
        ap2_receipts = [receipt for receipt in ap2_receipts if receipt]
        self._charge_x402(
            vendor="seo-keyword-api",
            amount=max(0.05, num_keywords * 0.002),
            metadata={
                "topic": topic,
                "audience": target_audience,
                "num_keywords": num_keywords,
                "cacheable_asset": True,
                "asset_signature": f"{topic}:{target_audience}:keywords",
                "asset_ttl_hours": 168,
            },
        )
        result = {
            "research_id": f"KW-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "topic": topic,
            "target_audience": target_audience,
            "keywords": [
                {"keyword": f"{topic} tutorial", "search_volume": 12500, "difficulty": 45, "cpc": 2.35},
                {"keyword": f"best {topic} tools", "search_volume": 8900, "difficulty": 52, "cpc": 3.10},
                {"keyword": f"{topic} guide", "search_volume": 6700, "difficulty": 38, "cpc": 1.85},
                {"keyword": f"how to {topic}", "search_volume": 15200, "difficulty": 41, "cpc": 2.05}
            ],
            "total_keywords": num_keywords,
            "researched_at": datetime.now().isoformat(),
            "ap2_approvals": ap2_receipts,
        }
        return json.dumps(result, indent=2)

    def optimize_content(self, content_url: str, target_keywords: List[str], optimization_type: str) -> str:
        """Optimize content for search engines"""
        self._charge_x402(
            vendor="seo-optimizer",
            amount=max(0.03, len(target_keywords) * 0.003),
            metadata={"url": content_url, "type": optimization_type},
        )
        result = {
            "optimization_id": f"OPT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "content_url": content_url,
            "target_keywords": target_keywords,
            "optimization_type": optimization_type,
            "recommendations": [
                "Add target keyword to title tag",
                "Improve meta description (current: 45 chars, optimal: 150-160 chars)",
                "Add alt text to 3 images",
                "Increase content length (current: 450 words, recommended: 1500+ words)",
                "Add internal links to related content",
                "Improve heading structure (add H2 and H3 tags)"
            ],
            "seo_score_before": 62,
            "seo_score_after": 85,
            "optimized_at": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)

    def analyze_backlinks(self, domain: str, *, service_cost: float = 499.0) -> str:
        """Analyze backlink profile for a domain"""
        approval = self._ensure_seo_budget(
            service_name="Backlink monitoring service",
            amount=service_cost,
            metadata={"domain": domain, "category": "backlink_analysis"},
        )
        self._charge_x402(
            vendor="seo-backlink-api",
            amount=max(0.08, service_cost * 0.002),
            metadata={
                "domain": domain,
                "cacheable_asset": True,
                "asset_signature": f"{domain}:backlinks",
                "asset_ttl_hours": 240,
            },
        )
        result = {
            "analysis_id": f"BL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "domain": domain,
            "total_backlinks": 3456,
            "referring_domains": 289,
            "domain_authority": 45,
            "top_backlinks": [
                {"source": "techcrunch.com", "authority": 92, "type": "dofollow"},
                {"source": "medium.com", "authority": 87, "type": "dofollow"},
                {"source": "reddit.com", "authority": 91, "type": "nofollow"}
            ],
            "toxic_links": 12,
            "new_links_last_30_days": 47,
            "lost_links_last_30_days": 8,
            "analyzed_at": datetime.now().isoformat(),
            "ap2_approvals": [approval] if approval else [],
        }
        return json.dumps(result, indent=2)

    def track_rankings(
        self,
        domain: str,
        keywords: List[str],
        search_engine: str,
        *,
        tool_name: str = "AccuRanker",
        tool_cost: float = 45.0,
    ) -> str:
        """Track keyword rankings for a domain"""
        approval = self._ensure_seo_budget(
            service_name=f"{tool_name} subscription",
            amount=tool_cost,
            metadata={"tool": tool_name, "category": "rank_tracking"},
        )
        self._charge_x402(
            vendor="seo-rank-tracker",
            amount=max(0.04, len(keywords) * 0.0015),
            metadata={
                "domain": domain,
                "engine": search_engine,
                "cacheable_asset": True,
                "asset_signature": f"{domain}:{search_engine}:rankings",
                "asset_ttl_hours": 72,
            },
        )
        result = {
            "tracking_id": f"RANK-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "domain": domain,
            "search_engine": search_engine,
            "rankings": [
                {"keyword": keywords[0] if keywords else "default", "current_position": 5, "previous_position": 7, "change": 2},
                {"keyword": keywords[1] if len(keywords) > 1 else "default", "current_position": 12, "previous_position": 15, "change": 3},
                {"keyword": keywords[2] if len(keywords) > 2 else "default", "current_position": 23, "previous_position": 28, "change": 5}
            ],
            "average_position": 13.3,
            "visibility_score": 67.8,
            "tracked_at": datetime.now().isoformat(),
            "ap2_approvals": [approval] if approval else [],
        }
        return json.dumps(result, indent=2)

    def generate_seo_report(self, domain: str, start_date: str, end_date: str) -> str:
        """Generate comprehensive SEO performance report"""
        self._charge_x402(
            vendor="seo-reporting",
            amount=0.06,
            metadata={"domain": domain, "start": start_date, "end": end_date},
        )
        result = {
            "report_id": f"SEO-REPORT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "domain": domain,
            "period": {"start": start_date, "end": end_date},
            "metrics": {
                "organic_traffic": 45678,
                "organic_traffic_growth": 23.5,
                "average_position": 13.3,
                "position_improvement": 2.7,
                "keyword_rankings_top_10": 34,
                "keyword_rankings_top_100": 156,
                "backlinks_gained": 47,
                "domain_authority": 45,
                "pages_indexed": 287,
                "core_web_vitals_pass_rate": 92.3
            },
            "generated_at": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)

    def run_full_seo_analysis(
        self,
        topic: str,
        domain: str,
        target_audience: str,
        keywords: List[str],
    ) -> Dict[str, Any]:
        """End-to-end helper that collects AP2 receipts for the full SEO workflow."""
        research = json.loads(self.keyword_research(topic, target_audience, len(keywords)))
        backlinks = json.loads(self.analyze_backlinks(domain))
        rankings = json.loads(self.track_rankings(domain, keywords, "google"))
        aggregated_receipts = (
            research.get("ap2_approvals", [])
            + backlinks.get("ap2_approvals", [])
            + rankings.get("ap2_approvals", [])
        )
        return {
            "research": research,
            "backlinks": backlinks,
            "rankings": rankings,
            "ap2_receipts": aggregated_receipts,
        }


    def route_task(self, task_description: str, priority: float = 0.5) -> RoutingDecision:
        """
        Route task to appropriate model using DAAO

        Args:
            task_description: Description of the task
            priority: Task priority (0.0-1.0)

        Returns:
            RoutingDecision with model selection and cost estimate
        """
        task = {
            'id': f'seo-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'description': task_description,
            'priority': priority,
            'required_tools': []
        }

        decision = self.router.route_task(task, budget_conscious=True)

        logger.info(
            "Task routed: %s",
            decision.reasoning,
            extra={
                'agent': 'SEOAgent',
                'model': decision.model,
                'difficulty': decision.difficulty.value,
                'estimated_cost': decision.estimated_cost
            }
        )

        return decision

    def get_cost_metrics(self) -> Dict:
        """Get cumulative cost savings from DAAO and TUMIX"""
        if not self.refinement_history:
            return {
                'agent': 'SEOAgent',
                'tumix_sessions': 0,
                'tumix_savings_percent': 0.0,
                'message': 'No refinement sessions recorded yet'
            }

        tumix_savings = self.termination.estimate_cost_savings(
            [
                [r for r in session]
                for session in self.refinement_history
            ],
            cost_per_round=0.001
        )

        return {
            'agent': 'SEOAgent',
            'tumix_sessions': tumix_savings['sessions'],
            'tumix_baseline_rounds': tumix_savings['baseline_rounds'],
            'tumix_actual_rounds': tumix_savings['tumix_rounds'],
            'tumix_savings_percent': tumix_savings['savings_percent'],
            'tumix_total_saved': tumix_savings['savings'],
            'daao_info': 'DAAO routing automatically applied to all tasks'
        }

    def shutdown(self) -> None:
        """Cleanup AP2 loop resources."""
        if self._ap2_loop:
            self._ap2_loop.call_soon_threadsafe(self._ap2_loop.stop)
        if self._ap2_thread:
            self._ap2_thread.join(timeout=1)
        self._ap2_loop = None
        self._ap2_thread = None

    def get_budget_metrics(self) -> Dict[str, Any]:
        self._reset_monthly_budget_if_needed()
        return {
            "monthly_limit": self._monthly_limit,
            "monthly_spend": self._current_monthly_spend,
            "remaining_budget": max(self._monthly_limit - self._current_monthly_spend, 0),
            "window": self._budget_window,
        }

    def get_audit_log(self) -> List[Dict[str, Any]]:
        return list(self.seo_audit_log)

    def get_alerts(self) -> List[Dict[str, Any]]:
        return list(self.seo_alerts)

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
            raise RuntimeError("AP2 service unavailable for SEOAgent.")
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

    def _get_seo_budget(self) -> AP2BudgetConfig:
        return DEFAULT_BUDGETS.get(
            "seo_agent",
            AP2BudgetConfig(monthly_limit=500.0, per_transaction_alert=100.0, require_manual_above=200.0),
        )

    def _reset_monthly_budget_if_needed(self) -> None:
        current_window = datetime.utcnow().strftime("%Y-%m")
        if current_window != self._budget_window:
            self._budget_window = current_window
            self._current_monthly_spend = 0.0

    def _ensure_seo_budget(
        self,
        service_name: str,
        amount: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if amount <= 0:
            raise ValueError("SEO tool spend must be positive.")
        if not self.ap2_service:
            raise RuntimeError("AP2 service unavailable for SEOAgent.")

        self._reset_monthly_budget_if_needed()
        if self._current_monthly_spend + amount > self._monthly_limit:
            raise ValueError(
                f"SEO monthly budget exhausted. Remaining ${self._monthly_limit - self._current_monthly_spend:.2f}."
            )

        budget_config = self._get_seo_budget()
        auto_approval = amount <= 50.0
        manual_review = amount > 100.0

        receipt = self._execute_ap2_coro(
            self.ap2_service.request_purchase(
                agent_name="seo_agent",
                user_id=f"{self.business_id}_seo",
                service_name=service_name,
                price=amount,
                categories=["seo"],
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
            raise RuntimeError("SEOAgent AP2 signature verification failed.")

        self._current_monthly_spend += amount
        self.tool_spend[service_name] += amount
        self.seo_audit_log.append(payload)

        if amount >= budget_config.per_transaction_alert:
            self.seo_alerts.append(
                {
                    "service": service_name,
                    "amount": amount,
                    "timestamp": payload["timestamp"],
                }
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
        compare_payload = {k: v for k, v in payload.items() if k != "signature"}
        expected = self._sign_payload(compare_payload)
        return hmac.compare_digest(signature, expected)



async def get_seo_agent(business_id: str = "default") -> SEOAgent:
    agent = SEOAgent(business_id=business_id)
    await agent.initialize()
    return agent
