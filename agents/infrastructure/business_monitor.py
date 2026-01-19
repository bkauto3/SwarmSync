"""
Business Generation Monitor

Tracks and monitors agent activity for generating 100s of businesses.
Provides real-time metrics, logs, and dashboard data.
Emits Prometheus metrics for dashboard visualization.
"""

import json
import os
import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict

from infrastructure.alert_bridge import AlertBridge

# Prometheus metrics
try:
    from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("prometheus_client not installed. Metrics will not be exported.")

logger = logging.getLogger(__name__)

# ==================== PROMETHEUS METRICS ====================
if PROMETHEUS_AVAILABLE:
    # Revenue and Cost
    revenue_counter = Counter('genesis_revenue_total', 'Total revenue generated (USD)')
    operating_cost_counter = Counter('genesis_operating_cost_total', 'Total operating costs (USD)')

    # Business metrics
    active_businesses_gauge = Gauge('genesis_active_businesses', 'Number of active businesses')
    total_businesses_counter = Counter('genesis_businesses_total', 'Total businesses created', ['status'])

    # Task metrics
    tasks_counter = Counter('genesis_tasks_total', 'Total tasks completed', ['status'])
    task_success_rate_gauge = Gauge('genesis_task_success_rate', 'Overall task success rate (0-1)')

    # Agent metrics
    agent_calls_counter = Counter('genesis_agent_calls_total', 'Total agent calls', ['agent_name'])
    agent_success_counter = Counter('genesis_agent_success_total', 'Successful agent calls', ['agent_name'])
    agent_execution_duration = Histogram('genesis_agent_execution_duration_seconds',
                                        'Agent execution duration', ['agent_name'])
    agent_execution_cost = Histogram('genesis_agent_execution_cost_dollars',
                                     'Agent execution cost in USD', ['agent_name'])
    agent_quality_score = Histogram('genesis_agent_quality_score',
                                    'Agent quality score (0-10)', ['agent_name'])
    agent_current_load = Gauge('genesis_agent_current_load',
                              'Current agent load percentage', ['agent_name'])
    agent_success_rate_gauge = Gauge('genesis_agent_success_rate',
                                     'Agent success rate (0-1)', ['agent_name'])

    # Human intervention
    human_interventions_counter = Counter('genesis_human_interventions_total',
                                          'Total human interventions required')

    # Component metrics
    components_counter = Counter('genesis_components_total', 'Total components generated',
                                 ['component_type', 'status'])

    # LLM usage
    llm_calls_counter = Counter('genesis_llm_calls_total', 'Total LLM API calls', ['provider'])

    # Cost projection
    monthly_cost_gauge = Gauge('genesis_monthly_cost_projection_dollars',
                              'Projected monthly cost in USD')

    # x402 spend
    x402_payments_counter = Counter(
        'genesis_x402_payments_total',
        'Total x402 payments processed',
        ['vendor', 'status'],
    )
    x402_spend_gauge = Gauge(
        'genesis_x402_spend_usdc',
        'Cumulative x402 spend in USD',
    )

    # VOIX metrics (Integration #74)
    voix_detection_counter = Counter(
        'genesis_voix_detections_total',
        'Total VOIX detection attempts',
        ['url', 'result']
    )
    voix_detection_rate_gauge = Gauge(
        'genesis_voix_detection_rate',
        'VOIX detection rate (% sites with tags)',
    )
    voix_invocation_counter = Counter(
        'genesis_voix_invocations_total',
        'Total VOIX tool invocations',
        ['tool_name', 'status']
    )
    voix_invocation_success_rate_gauge = Gauge(
        'genesis_voix_invocation_success_rate',
        'VOIX invocation success rate (0-1)',
    )
    voix_discovery_time_histogram = Histogram(
        'genesis_voix_discovery_time_seconds',
        'VOIX discovery time in seconds',
        ['mode']
    )
    voix_fallback_counter = Counter(
        'genesis_voix_fallback_total',
        'Total fallbacks from VOIX to Skyvern',
        ['reason']
    )
    voix_fallback_rate_gauge = Gauge(
        'genesis_voix_fallback_rate',
        'VOIX fallback rate (Skyvern usage)',
    )
    voix_performance_improvement_gauge = Gauge(
        'genesis_voix_performance_improvement_factor',
        'VOIX performance improvement factor (speedup)',
    )

    # System info
    system_info = Info('genesis_system', 'Genesis system information')
    system_info.info({
        'version': '1.0.0',
        'phase': '6_optimization',
        'deployment': 'production'
    })


@dataclass
class BusinessGenerationMetrics:
    """Metrics for a single business generation."""
    business_name: str
    business_type: str
    start_time: float
    end_time: Optional[float] = None
    status: str = "in_progress"  # in_progress, completed, failed
    components_requested: int = 0
    components_completed: int = 0
    components_failed: int = 0
    files_generated: int = 0
    lines_of_code: int = 0
    cost_usd: float = 0.0
    errors: List[str] = field(default_factory=list)
    agent_calls: int = 0
    vertex_ai_calls: int = 0
    local_llm_calls: int = 0
    retry_count: int = 0
    
    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    @property
    def success_rate(self) -> float:
        total = self.components_completed + self.components_failed
        if total == 0:
            return 0.0
        return (self.components_completed / total) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['duration_seconds'] = self.duration_seconds
        data['success_rate'] = self.success_rate
        return data


class BusinessMonitor:
    """
    Monitor for tracking agent business generation activity.
    
    Stores metrics for all businesses being generated, provides
    real-time stats, and writes logs for dashboard consumption.
    """
    
    def __init__(self, log_dir: Path = None, prometheus_port: int = 8000):
        self.log_dir = log_dir or Path("logs/business_generation")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # In-memory tracking
        self.businesses: Dict[str, BusinessGenerationMetrics] = {}
        self.global_stats = {
            "total_businesses": 0,
            "completed": 0,
            "failed": 0,
            "in_progress": 0,
            "total_components": 0,
            "total_files": 0,
            "total_lines_of_code": 0,
            "total_cost_usd": 0.0,
            "start_time": time.time(),
            "rubric_audits": 0,
            "rubric_alerts": 0,
            "rubric_audit_goal_met": False,
            "hallucination_checks": 0,
            "hallucination_failures": 0,
            "hallucination_rate": 0.0,
            "ap2_events": 0,
            "ap2_failures": 0,
            "ap2_spend": 0.0,
            "policy_audits": 0,
            "policy_alerts": 0,
            "x402_events": 0,
            "x402_spend": 0.0,
            "x402_failures": 0,
        }

        # Component tracking by type
        self.component_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"attempted": 0, "succeeded": 0, "failed": 0})

        # Agent usage tracking
        self.agent_usage = defaultdict(int)

        # Binary RAR audit log
        self.hallucination_events: List[Dict[str, Any]] = []
        self.policy_events: List[Dict[str, Any]] = []
        self.ap2_events: List[Dict[str, Any]] = []
        self.x402_transactions: List[Dict[str, Any]] = []

        # Rubric auditing
        self.rubric_reports: List[Dict[str, Any]] = []
        self.ap2_budget_configs: Dict[str, Dict[str, float]] = {}
        self.x402_budget_configs: Dict[str, Dict[str, float]] = {}
        self.x402_vendor_failures: Dict[str, int] = defaultdict(int)
        self.pending_authorizations: Dict[str, Dict[str, Any]] = {}
        self.x402_alert_log = self.log_dir / "x402_alerts.jsonl"
        self.x402_wallet_start = float(os.getenv("X402_WALLET_START_USDC", "500"))
        self.x402_wallet_remaining = self.x402_wallet_start
        self.x402_wallet_warned = False
        self.alert_bridge = AlertBridge()

        # Start Prometheus metrics server
        if PROMETHEUS_AVAILABLE:
            try:
                start_http_server(prometheus_port)
                logger.info(f"Prometheus metrics server started on port {prometheus_port}")
            except Exception as e:
                logger.warning(f"Could not start Prometheus server: {e}")

        logger.info(f"Business monitor initialized (log_dir={self.log_dir})")
    
    def start_business(self, name: str, business_type: str, components: List[str]) -> str:
        """Start tracking a new business generation."""
        business_id = f"{business_type}_{name.lower().replace(' ', '_')}_{int(time.time())}"
        
        metrics = BusinessGenerationMetrics(
            business_name=name,
            business_type=business_type,
            start_time=time.time(),
            components_requested=len(components)
        )
        
        self.businesses[business_id] = metrics
        self.global_stats["total_businesses"] += 1
        self.global_stats["in_progress"] += 1

        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            total_businesses_counter.labels(status='started').inc()
            active_businesses_gauge.set(self.global_stats["in_progress"])

        logger.info(f"Started tracking: {name} (type={business_type}, components={len(components)})")
        self._write_event("business_started", {
            "business_id": business_id,
            "name": name,
            "type": business_type,
            "components": components
        })

        return business_id
    
    def record_component_start(self, business_id: str, component_name: str, agent_name: str):
        """Record that a component generation has started."""
        if business_id not in self.businesses:
            logger.warning(f"Unknown business_id: {business_id}")
            return
        
        self.component_stats[component_name]["attempted"] += 1
        self.agent_usage[agent_name] += 1
        self.businesses[business_id].agent_calls += 1

        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            agent_calls_counter.labels(agent_name=agent_name).inc()
            components_counter.labels(component_type=component_name, status='started').inc()

        self._write_event("component_started", {
            "business_id": business_id,
            "component": component_name,
            "agent": agent_name
        })
    
    def record_component_complete(self, business_id: str, component_name: str, 
                                 lines_of_code: int, cost: float, used_vertex: bool):
        """Record successful component generation."""
        if business_id not in self.businesses:
            return
        
        biz = self.businesses[business_id]
        biz.components_completed += 1
        biz.files_generated += 1
        biz.lines_of_code += lines_of_code
        biz.cost_usd += cost
        
        if used_vertex:
            biz.vertex_ai_calls += 1
        else:
            biz.local_llm_calls += 1
        
        self.component_stats[component_name]["succeeded"] += 1
        self.global_stats["total_components"] += 1
        self.global_stats["total_files"] += 1
        self.global_stats["total_lines_of_code"] += lines_of_code
        self.global_stats["total_cost_usd"] += cost

        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            components_counter.labels(component_type=component_name, status='completed').inc()
            tasks_counter.labels(status='completed').inc()
            operating_cost_counter.inc(cost)
            llm_calls_counter.labels(provider='vertex_ai' if used_vertex else 'local').inc()
            # Update monthly cost projection (current cost * 30 days)
            monthly_cost_gauge.set(self.global_stats["total_cost_usd"] * 30)

        self._write_event("component_completed", {
            "business_id": business_id,
            "component": component_name,
            "lines": lines_of_code,
            "cost": cost,
            "vertex_ai": used_vertex
        })
    
    def record_component_failed(self, business_id: str, component_name: str, error: str):
        """Record failed component generation."""
        if business_id not in self.businesses:
            return
        
        biz = self.businesses[business_id]
        biz.components_failed += 1
        biz.errors.append(f"{component_name}: {error}")

        self.component_stats[component_name]["failed"] += 1

        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            components_counter.labels(component_type=component_name, status='failed').inc()
            tasks_counter.labels(status='failed').inc()

        self._write_event("component_failed", {
            "business_id": business_id,
            "component": component_name,
            "error": error
        })
    
    def record_retry(self, business_id: str, component_name: str, attempt: int):
        """Record a retry attempt."""
        if business_id not in self.businesses:
            return
        
        self.businesses[business_id].retry_count += 1
        
        self._write_event("component_retry", {
            "business_id": business_id,
            "component": component_name,
            "attempt": attempt
        })
    
    def complete_business(self, business_id: str, success: bool):
        """Mark a business as completed."""
        if business_id not in self.businesses:
            return
        
        biz = self.businesses[business_id]
        biz.end_time = time.time()
        biz.status = "completed" if success else "failed"
        
        self.global_stats["in_progress"] -= 1
        if success:
            self.global_stats["completed"] += 1
        else:
            self.global_stats["failed"] += 1

        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            total_businesses_counter.labels(status='completed' if success else 'failed').inc()
            active_businesses_gauge.set(self.global_stats["in_progress"])
            # Calculate and update success rate
            total = self.global_stats["completed"] + self.global_stats["failed"]
            if total > 0:
                success_rate = self.global_stats["completed"] / total
                task_success_rate_gauge.set(success_rate)
            # Update revenue (mock calculation: $100 per successful business)
            if success:
                revenue_counter.inc(100)

        logger.info(f"Completed: {biz.business_name} ({biz.duration_seconds:.1f}s, {biz.components_completed}/{biz.components_requested} components)")

        self._write_event("business_completed", {
            "business_id": business_id,
            "success": success,
            "duration": biz.duration_seconds,
            "components": biz.components_completed,
            "cost": biz.cost_usd
        })

        # Write summary
        self._write_business_summary(business_id, biz)
    
    def get_business_metrics(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific business."""
        if business_id not in self.businesses:
            return None
        return self.businesses[business_id].to_dict()
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global statistics."""
        stats = self.global_stats.copy()
        stats["uptime_seconds"] = time.time() - stats["start_time"]
        stats["avg_cost_per_business"] = (
            stats["total_cost_usd"] / stats["completed"] if stats["completed"] > 0 else 0.0
        )
        stats["avg_components_per_business"] = (
            stats["total_components"] / stats["completed"] if stats["completed"] > 0 else 0.0
        )
        return stats
    
    def get_component_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get per-component statistics."""
        result = {}
        for component, stats in self.component_stats.items():
            total = stats["attempted"]
            result[component] = {
                **stats,
                "success_rate": (stats["succeeded"] / total * 100) if total > 0 else 0.0
            }
        return result
    
    def get_agent_usage(self) -> Dict[str, int]:
        """Get agent usage statistics."""
        return dict(self.agent_usage)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all data formatted for dashboard display."""
        return {
            "global_stats": self.get_global_stats(),
            "component_stats": self.get_component_stats(),
            "agent_usage": self.get_agent_usage(),
            "active_businesses": [
                {
                    "id": bid,
                    "name": biz.business_name,
                    "type": biz.business_type,
                    "progress": f"{biz.components_completed}/{biz.components_requested}",
                    "duration": f"{biz.duration_seconds:.1f}s",
                    "status": biz.status
                }
                for bid, biz in self.businesses.items()
                if biz.status == "in_progress"
            ],
            "recent_completions": [
                {
                    "name": biz.business_name,
                    "type": biz.business_type,
                    "duration": f"{biz.duration_seconds:.1f}s",
                    "components": biz.components_completed,
                    "cost": f"${biz.cost_usd:.4f}",
                    "success_rate": f"{biz.success_rate:.1f}%"
                }
                for bid, biz in sorted(
                    self.businesses.items(),
                    key=lambda x: x[1].end_time or 0,
                    reverse=True
                )[:10]
                if biz.status in ["completed", "failed"]
            ],
            "rubric_reports": list(reversed(self.rubric_reports[-10:])),
            "hallucination_events": list(reversed(self.hallucination_events[-10:])),
            "policy_events": list(reversed(self.policy_events[-10:])),
            "ap2_events": list(reversed(self.ap2_events[-10:])),
            "ap2_budgets": self.ap2_budget_configs,
            "x402_transactions": list(reversed(self.x402_transactions[-50:])),
            "x402_budgets": self.x402_budget_configs,
        }

    def record_rubric_report(self, business_name: str, business_type: str, report: Dict[str, Any]):
        """Record rubric evaluation output and emit dashboard event."""
        overall_score = report.get("overall_score")
        coverage = report.get("coverage_ratio", 0.0)
        total_weight = report.get("total_weight", 0.0)

        if total_weight == 0 or overall_score is None:
            status = "pending"
            reward = 0.0
        elif overall_score >= 0.85 and coverage >= 0.7:
            status = "pass"
            reward = 1.0
        elif overall_score >= 0.6 and coverage >= 0.5:
            status = "partial"
            reward = 0.5
        else:
            status = "alert"
            reward = 0.0

        entry = {
            "business_name": business_name,
            "business_type": business_type,
            "overall_score": overall_score,
            "coverage_ratio": coverage,
            "status": status,
            "reward": reward,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_reports": report.get("task_reports", {}),
        }

        self.rubric_reports.append(entry)
        self.rubric_reports = self.rubric_reports[-100:]

        self.global_stats["rubric_audits"] += 1
        if status == "alert":
            self.global_stats["rubric_alerts"] += 1
        self.global_stats["rubric_audit_goal_met"] = self.global_stats["rubric_audits"] >= 100

        self._write_event("rubric_report", entry)
        self.write_dashboard_snapshot()

    def record_hallucination_event(self, agent_name: str, result: Dict[str, Any]):
        """Record Binary RAR verification metrics."""
        reward = result.get("reward")
        coverage = result.get("coverage")
        status = result.get("status")

        if reward is not None:
            self.global_stats["hallucination_checks"] += 1
            if reward < 1.0:
                self.global_stats["hallucination_failures"] += 1
            checks = self.global_stats["hallucination_checks"]
            failures = self.global_stats["hallucination_failures"]
            self.global_stats["hallucination_rate"] = failures / checks if checks else 0.0

        event = {
            "agent": agent_name,
            "status": status,
            "reward": reward,
            "coverage": coverage,
            "supporting_docs": result.get("supporting_docs", []),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.hallucination_events.append(event)
        self.hallucination_events = self.hallucination_events[-200:]
        self._write_event("binary_rar_eval", event)
        self.write_dashboard_snapshot()

    def record_ap2_event(self, agent_name: str, payload: Dict[str, Any]):
        """Track AP2 intent/cart events for visibility."""
        self.global_stats["ap2_events"] += 1
        cost = payload.get("cost", 0.0)
        self.global_stats["ap2_spend"] += cost
        status = payload.get("status")
        if status != "approved":
            self.global_stats["ap2_failures"] += 1

        event = {
            "agent": agent_name,
            "event_type": payload.get("event_type"),
            "status": status,
            "cost": cost,
            "extra": payload.get("extra", {}),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.ap2_events.append(event)
        self.ap2_events = self.ap2_events[-200:]
        self._write_event("ap2_event", event)
        self.write_dashboard_snapshot()

    def record_policy_audit(self, agent_name: str, verdict: Dict[str, Any]):
        """Record policy audit verdicts for dashboard + alerts."""
        self.global_stats["policy_audits"] += 1
        if verdict.get("status") == "violation":
            self.global_stats["policy_alerts"] += 1

        event = {
            "agent": agent_name,
            "status": verdict.get("status"),
            "violations": verdict.get("violations", []),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.policy_events.append(event)
        self.policy_events = self.policy_events[-200:]
        self._write_event("policy_audit", event)
        self.write_dashboard_snapshot()

    def register_ap2_budgets(self, configs: Dict[str, Any]):
        """Expose AP2 budget configuration on the dashboard."""
        if not configs:
            return
        normalized: Dict[str, Dict[str, float]] = {}
        for agent, cfg in configs.items():
            if cfg is None:
                continue
            if hasattr(cfg, "monthly_limit"):
                normalized[agent] = {
                    "monthly_limit": getattr(cfg, "monthly_limit", 0.0),
                    "per_transaction_alert": getattr(cfg, "per_transaction_alert", 0.0),
                    "require_manual_above": getattr(cfg, "require_manual_above", 0.0),
                }
            elif isinstance(cfg, dict):
                normalized[agent] = {
                    "monthly_limit": cfg.get("monthly_limit", 0.0),
                    "per_transaction_alert": cfg.get("per_transaction_alert", 0.0),
                    "require_manual_above": cfg.get("require_manual_above", 0.0),
                }
        if normalized:
            self.ap2_budget_configs.update(normalized)

    def register_x402_budgets(self, configs: Dict[str, Any]):
        """Expose x402 budget configuration on the dashboard."""
        if not configs:
            return
        normalized: Dict[str, Dict[str, float]] = {}
        for agent, cfg in configs.items():
            if cfg is None:
                continue
            if hasattr(cfg, "daily_limit_usdc"):
                normalized[agent] = {
                    "daily_limit": getattr(cfg, "daily_limit_usdc", 0.0),
                    "max_payment_per_request": getattr(cfg, "max_payment_per_request", 0.0),
                }
            elif isinstance(cfg, dict):
                normalized[agent] = {
                    "daily_limit": cfg.get("daily_limit_usdc", 0.0),
                    "max_payment_per_request": cfg.get("max_payment_per_request", 0.0),
                }
        if normalized:
            self.x402_budget_configs.update(normalized)

    def record_x402_payment(self, agent_name: str, payload: Dict[str, Any]):
        """Track x402 payments for dashboards and alerts."""
        amount = payload.get("amount_usdc", 0.0)
        success = payload.get("success", True)
        vendor = payload.get("vendor") or "unknown"
        self.global_stats["x402_events"] += 1

    def record_voix_event(
        self,
        agent_name: str,
        event_type: str,
        payload: Dict[str, Any]
    ):
        """
        Track VOIX events for dashboards and alerts.
        
        Args:
            agent_name: Name of agent using VOIX
            event_type: Type of event ('detection', 'invocation', 'fallback')
            payload: Event data
        """
        if not PROMETHEUS_AVAILABLE:
            return

        if event_type == "detection":
            url = payload.get("url", "unknown")
            detected = payload.get("detected", False)
            result = "success" if detected else "failure"
            voix_detection_counter.labels(url=url, result=result).inc()
            
            # Update detection rate (calculate from stats if available)
            stats = payload.get("stats", {})
            if stats:
                total = stats.get("total_detections", 0)
                successful = stats.get("successful_detections", 0)
                if total > 0:
                    rate = (successful / total) * 100
                    voix_detection_rate_gauge.set(rate)

        elif event_type == "invocation":
            tool_name = payload.get("tool_name", "unknown")
            success = payload.get("success", False)
            status = "success" if success else "failure"
            voix_invocation_counter.labels(tool_name=tool_name, status=status).inc()
            
            # Update success rate (calculate from stats if available)
            stats = payload.get("stats", {})
            if stats:
                total = stats.get("total_invocations", 0)
                successful = stats.get("successful_invocations", 0)
                if total > 0:
                    rate = successful / total
                    voix_invocation_success_rate_gauge.set(rate)

        elif event_type == "fallback":
            reason = payload.get("reason", "unknown")
            voix_fallback_counter.labels(reason=reason).inc()
            
            # Update fallback rate (calculate from stats if available)
            stats = payload.get("stats", {})
            if stats:
                total = stats.get("total_attempts", 0)
                fallbacks = stats.get("fallback_count", 0)
                if total > 0:
                    rate = (fallbacks / total) * 100
                    voix_fallback_rate_gauge.set(rate)

        # Track discovery time
        discovery_time = payload.get("discovery_time_seconds")
        if discovery_time is not None:
            mode = payload.get("mode", "unknown")
            voix_discovery_time_histogram.labels(mode=mode).observe(discovery_time)

        # Track performance improvement
        improvement_factor = payload.get("performance_improvement_factor")
        if improvement_factor is not None:
            voix_performance_improvement_gauge.set(improvement_factor)

        # Log event
        logger.debug(f"[VOIX] {event_type} event from {agent_name}: {payload}")

    def _update_authorization_state(self, event: Dict[str, Any]) -> None:
        auth_id = event.get("authorization_id")
        if not auth_id:
            return
        mode = event.get("mode")
        if mode == "authorized":
            self.pending_authorizations[auth_id] = {
                "vendor": event.get("vendor"),
                "timestamp": event["timestamp"],
            }
        elif mode in {"capture", "authorization_cancelled"}:
            self.pending_authorizations.pop(auth_id, None)

    def _raise_x402_alert(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "extra": extra or {},
        }
        logger.warning("X402 alert: %s | %s", message, extra or {})
        with open(self.x402_alert_log, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(alert) + "\n")
        if self.alert_bridge:
            self.alert_bridge.dispatch("x402_alert", alert)

    def get_stale_authorizations(self, max_age_seconds: int = 3600) -> List[Dict[str, Any]]:
        """Return authorizations that have not been captured within the TTL."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
        stale = []
        for auth_id, meta in list(self.pending_authorizations.items()):
            ts = datetime.fromisoformat(meta["timestamp"])
            if ts < cutoff:
                meta_copy = dict(meta)
                meta_copy["authorization_id"] = auth_id
                stale.append(meta_copy)
        return stale

    def _write_event(self, event_type: str, data: Dict[str, Any]):
        """Write an event to the log file."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": data
        }
        
        # Write to events log (JSONL format)
        events_file = self.log_dir / "events.jsonl"
        with open(events_file, "a") as f:
            f.write(json.dumps(event) + "\n")
    
    def _write_business_summary(self, business_id: str, metrics: BusinessGenerationMetrics):
        """Write a summary file for a completed business."""
        summary_file = self.log_dir / f"{business_id}_summary.json"
        with open(summary_file, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)
    
    def write_dashboard_snapshot(self):
        """Write current dashboard data to file."""
        snapshot_file = self.log_dir / "dashboard_snapshot.json"
        with open(snapshot_file, "w") as f:
            json.dump(self.get_dashboard_data(), f, indent=2)

    def get_rolling_statistics(self, window_days: int = 7) -> Dict[str, Any]:
        """Aggregate business metrics over the last N days using summary files."""
        window_days = max(1, int(window_days))
        cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=window_days)).timestamp()
        summaries = []
        for summary_path in self.log_dir.glob("*_summary.json"):
            try:
                data = json.loads(summary_path.read_text())
            except Exception:
                continue
            end_ts = data.get("end_time") or data.get("start_time") or 0
            if end_ts >= cutoff_ts:
                summaries.append(data)

        if not summaries:
            return {
                "window_days": window_days,
                "businesses_built": 0,
                "success_rate": 0.0,
                "avg_quality_score": 0.0,
                "total_revenue": 0.0,
                "active_businesses": self.global_stats.get("in_progress", 0),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

        completed = sum(1 for s in summaries if s.get("status") == "completed")
        total_quality = sum(s.get("quality_score", s.get("success_rate", 0.0)) for s in summaries)
        total_revenue = sum(
            s.get("revenue_usd", s.get("net_revenue", s.get("cost_usd", 0.0))) for s in summaries
        )

        stats = {
            "window_days": window_days,
            "businesses_built": len(summaries),
            "success_rate": round((completed / len(summaries)) * 100, 2),
            "avg_quality_score": round(total_quality / len(summaries), 2),
            "total_revenue": round(total_revenue, 2),
            "active_businesses": self.global_stats.get("in_progress", 0),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        stats_file = self.log_dir / f"rolling_stats_{window_days}d.json"
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)
        return stats


# Global monitor instance
_monitor: Optional[BusinessMonitor] = None


def get_monitor() -> BusinessMonitor:
    """Get or create the global monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = BusinessMonitor()
    return _monitor
