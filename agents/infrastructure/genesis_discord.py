"""
Genesis Discord Integration
===========================

Provides rich Discord webhook notifications for every major Genesis event.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple
import json

import httpx

HexColor = int


class GenesisDiscord:
    """Convenience wrapper around Discord webhooks."""

    COLOR_INFO: HexColor = 0x3498DB
    COLOR_PROGRESS: HexColor = 0xF39C12
    COLOR_SUCCESS: HexColor = 0x2ECC71
    COLOR_ERROR: HexColor = 0xE74C3C
    COLOR_ANALYTICS: HexColor = 0x9B59B6
    COLOR_HOPX: HexColor = 0x95A5A6

    def __init__(
        self,
        *,
        send_hook: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
        timeout: float = 10.0,
    ):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._send_hook = send_hook
        self._preferences = self._load_preferences()
        self.progress_batch_size = int(os.getenv("DISCORD_PROGRESS_BATCH_SIZE", "3"))
        self._progress_buffer: Dict[Tuple[str, str], list[str]] = {}
        self.webhooks = {
            "dashboard": os.getenv("DISCORD_WEBHOOK_DASHBOARD"),
            "commands": os.getenv("DISCORD_WEBHOOK_COMMANDS"),
            "alerts": os.getenv("DISCORD_WEBHOOK_ALERTS"),
            "deployments": os.getenv("DISCORD_WEBHOOK_DEPLOYMENTS"),
            "metrics": os.getenv("DISCORD_WEBHOOK_METRICS"),
            "revenue": os.getenv("DISCORD_WEBHOOK_REVENUE"),
            "errors": os.getenv("DISCORD_WEBHOOK_ERRORS"),
            "hopx_env": os.getenv("DISCORD_WEBHOOK_HOPX_ENVIRONMENTS"),
            "hopx_errors": os.getenv("DISCORD_WEBHOOK_HOPX_ERRORS"),
        }

    # ------------------------------------------------------------------ #
    # Lifecycle helpers
    # ------------------------------------------------------------------ #

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _load_preferences(self) -> Dict[str, Any]:
        path = os.getenv("DISCORD_PREFERENCES_PATH", "config/discord_preferences.json")
        pref_path = Path(path)
        if not pref_path.exists():
            return {"notification_level": 3, "muted_channels": [], "muted_agents": []}
        try:
            return json.loads(pref_path.read_text(encoding="utf-8"))
        except Exception:
            return {"notification_level": 3, "muted_channels": [], "muted_agents": []}

    def _should_send(self, channel: str, level: int, agent_name: Optional[str] = None) -> bool:
        prefs = self._preferences or {}
        muted_channels = set(prefs.get("muted_channels", []))
        muted_agents = set(prefs.get("muted_agents", []))
        notification_level = int(prefs.get("notification_level", 3))
        if channel in muted_channels:
            return False
        if agent_name and agent_name in muted_agents:
            return False
        return level <= notification_level

    async def _send(
        self,
        channel: str,
        embed: Dict[str, Any],
        level: int = 3,
        *,
        agent_name: Optional[str] = None,
    ) -> None:
        webhook = self.webhooks.get(channel)
        if not webhook or not self._should_send(channel, level, agent_name):
            return  # channel not configured yet
        payload = {"embeds": [embed]}
        if self._send_hook:
            await self._send_hook(webhook, payload)
            return
        client = await self._ensure_client()
        response = await client.post(webhook, json=payload)
        response.raise_for_status()

    def _embed(
        self, *, title: str, description: str, color: HexColor, footer: Optional[str] = None
    ) -> Dict[str, Any]:
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if footer:
            embed["footer"] = {"text": footer}
        return embed

    # ------------------------------------------------------------------ #
    # System lifecycle
    # ------------------------------------------------------------------ #

    async def genesis_started(self) -> None:
        await self._send(
            "dashboard",
            self._embed(
                title="🚀 Genesis Agent System Started",
                description="All 21 agents initialized and ready for autonomous execution.",
                color=self.COLOR_INFO,
                footer="Genesis Meta Agent",
            ),
        )

    async def genesis_shutdown(self) -> None:
        await self._send(
            "dashboard",
            self._embed(
                title="⛔ Genesis Agent System Shutdown",
                description="System going offline. Pending builds will resume next boot.",
                color=self.COLOR_ERROR,
            ),
        )

    # ------------------------------------------------------------------ #
    # Business lifecycle
    # ------------------------------------------------------------------ #

    async def business_build_started(self, business_id: str, name: str, idea: str) -> None:
        await self._send(
            "dashboard",
            self._embed(
                title=f"🏗️ Build Started: {name}",
                description=f"**Business ID:** {business_id}\n**Idea:** {idea}",
                color=self.COLOR_PROGRESS,
                footer="Genesis Meta Agent",
            ),
        )

    async def business_build_completed(
        self, business_id: str, url: str, metrics: Dict[str, Any]
    ) -> None:
        embed = self._embed(
            title=f"✅ Build Complete: {metrics.get('name', business_id)}",
            description=(
                f"**Live URL:** {url}\n"
                f"**Quality Score:** {metrics.get('quality_score', 'N/A')}/100\n"
                f"**Build Time:** {metrics.get('build_time', 'unknown')}"
            ),
            color=self.COLOR_SUCCESS,
        )
        await self._send("dashboard", embed)
        await self._send("deployments", embed)

    async def x402_spend_summary(
        self,
        business_id: str,
        business_name: str,
        summary: Dict[str, Any],
    ) -> None:
        vendor_lines = ", ".join(
            f"{vendor}: ${amount:.2f}" for vendor, amount in summary.get("by_vendor", {}).items()
        ) or "n/a"
        agent_lines = ", ".join(
            f"{agent}: ${amount:.2f}" for agent, amount in summary.get("by_agent", {}).items()
        ) or "n/a"
        description = (
            f"**Total Spend:** ${summary.get('total_spend', 0):.2f}\n"
            f"**Vendors:** {vendor_lines}\n"
            f"**Agents:** {agent_lines}\n"
            f"**Revenue Potential:** ${summary.get('revenue_potential', 0):.2f}\n"
            f"**ROI Delta:** ${summary.get('roi_delta', 0):.2f}"
        )
        embed = self._embed(
            title=f"💸 x402 Spend Summary · {business_name}",
            description=description,
            color=self.COLOR_ANALYTICS,
            footer=f"Business ID: {business_id}",
        )
        await self._send("dashboard", embed, level=2)
        await self._send("metrics", embed, level=2)

    # ------------------------------------------------------------------ #
    # Agent lifecycle
    # ------------------------------------------------------------------ #

    async def agent_started(self, business_id: str, agent_name: str, task: str) -> None:
        await self._send(
            "dashboard",
            self._embed(
                title=f"🤖 {agent_name} Started",
                description=f"**Task:** {task}",
                color=self.COLOR_INFO,
                footer=f"Agent: {agent_name} • Business: {business_id}",
            ),
            level=3,
            agent_name=agent_name,
        )

    async def agent_progress(self, business_id: str, agent_name: str, message: str) -> None:
        key = (business_id, agent_name)
        buffer = self._progress_buffer.setdefault(key, [])
        buffer.append(message)
        if self.progress_batch_size <= 1 or len(buffer) >= self.progress_batch_size:
            await self._flush_progress_buffer(business_id, agent_name)

    async def agent_completed(self, business_id: str, agent_name: str, result: str) -> None:
        await self._flush_progress_buffer(business_id, agent_name)
        await self._send(
            "dashboard",
            self._embed(
                title=f"✅ {agent_name} Complete",
                description=f"**Result:** {result}",
                color=self.COLOR_SUCCESS,
                footer=f"Agent: {agent_name} • Business: {business_id}",
            ),
            level=2,
            agent_name=agent_name,
        )

    async def agent_error(self, business_id: str, agent_name: str, error_message: str) -> None:
        await self._flush_progress_buffer(business_id, agent_name)
        await self._send(
            "errors",
            self._embed(
                title=f"❌ {agent_name} Error",
                description=f"**Business:** {business_id}\n**Error:** {error_message}",
                color=self.COLOR_ERROR,
                footer=f"Agent: {agent_name}",
            ),
            level=1,
            agent_name=agent_name,
        )

    # ------------------------------------------------------------------ #
    # Deployment + revenue
    # ------------------------------------------------------------------ #

    async def deployment_success(self, business_name: str, url: str, metrics: Dict[str, Any]) -> None:
        await self._send(
            "deployments",
            self._embed(
                title=f"🌐 {business_name} Deployed",
                description=(
                    f"**Live at:** {url}\n"
                    f"**Build time:** {metrics.get('build_time', 'unknown')}\n"
                    f"**Quality:** {metrics.get('quality_score', 'N/A')}/100"
                ),
                color=self.COLOR_SUCCESS,
                footer="Deploy Agent",
            ),
            level=2,
        )

    async def deployment_failed(self, business_name: str, error: str) -> None:
        await self._send(
            "errors",
            self._embed(
                title=f"❌ {business_name} Deployment Failed",
                description=f"**Error:** {error}",
                color=self.COLOR_ERROR,
            ),
            level=1,
        )

    async def payment_received(self, business_name: str, amount: float, customer_email: str) -> None:
        await self._send(
            "revenue",
            self._embed(
                title=f"💰 Payment Received: ${amount:.2f}",
                description=f"**Business:** {business_name}\n**Customer:** {customer_email}",
                color=self.COLOR_SUCCESS,
                footer="Stripe Integration",
            ),
            level=2,
        )

    async def refund_processed(self, business_name: str, amount: float, reason: str) -> None:
        await self._send(
            "revenue",
            self._embed(
                title=f"↩️ Refund Issued: ${amount:.2f}",
                description=f"**Business:** {business_name}\n**Reason:** {reason}",
                color=self.COLOR_INFO,
                footer="Billing Agent",
            ),
        )

    async def subscription_update(
        self,
        business_name: str,
        customer_id: str,
        plan_id: str,
        action: str,
    ) -> None:
        description = (
            f"**Customer:** {customer_id}\n"
            f"**Plan:** {plan_id}\n"
            f"**Action:** {action.title()}"
        )
        color = self.COLOR_SUCCESS if action == "create" else self.COLOR_INFO
        await self._send(
            "revenue",
            self._embed(
                title="📦 Subscription Update",
                description=description,
                color=color,
                footer=business_name,
            ),
        )
        if action == "cancel":
            await self._send(
                "alerts",
                self._embed(
                    title="⚠️ Subscription Cancelled",
                    description=description,
                    color=self.COLOR_ERROR,
                    footer=business_name,
                ),
            )

    # ------------------------------------------------------------------ #
    # HopX lifecycle
    # ------------------------------------------------------------------ #

    async def hopx_environment_created(self, business_id: str, env_id: str, template: str) -> None:
        await self._send(
            "hopx_env",
            self._embed(
                title="🔧 HopX Environment Created",
                description=(
                    f"**Business ID:** {business_id}\n"
                    f"**Environment ID:** {env_id}\n"
                    f"**Template:** {template}"
                ),
                color=self.COLOR_INFO,
            ),
            level=4,
        )

    async def hopx_environment_destroyed(
        self, business_id: str, env_id: str, lifetime_seconds: float
    ) -> None:
        await self._send(
            "hopx_env",
            self._embed(
                title="🗑️ HopX Environment Destroyed",
                description=(
                    f"**Business ID:** {business_id}\n"
                    f"**Environment ID:** {env_id}\n"
                    f"**Lifetime:** {lifetime_seconds:.1f}s"
                ),
                color=self.COLOR_HOPX,
            ),
            level=4,
        )

    async def hopx_environment_stuck(self, env_id: str, age_hours: float) -> None:
        embed = self._embed(
            title="⚠️ HopX Environment Stuck",
            description=f"**Environment ID:** {env_id}\n**Age:** {age_hours:.1f} hours",
            color=self.COLOR_ERROR,
        )
        await self._send("hopx_errors", embed)
        await self._send("alerts", embed, level=2)

    async def hopx_api_error(self, error_message: str) -> None:
        await self._send(
            "hopx_errors",
            self._embed(
                title="❌ HopX API Error",
                description=f"**Error:** {error_message}",
                color=self.COLOR_ERROR,
            ),
            level=1,
        )

    # ------------------------------------------------------------------ #
    # Analytics
    # ------------------------------------------------------------------ #

    async def voix_metrics_report(
        self,
        detection_rate: float,
        invocation_success_rate: float,
        fallback_rate: float,
        avg_discovery_time_ms: float,
        performance_improvement_factor: float
    ) -> None:
        """
        Report VOIX metrics to Discord.
        
        Args:
            detection_rate: VOIX detection rate (% sites with tags)
            invocation_success_rate: VOIX invocation success rate (0-1)
            fallback_rate: VOIX fallback rate (% Skyvern usage)
            avg_discovery_time_ms: Average discovery time in milliseconds
            performance_improvement_factor: Performance improvement factor (speedup)
        """
        embed = {
            "title": "📊 VOIX Metrics Report (Integration #74)",
            "color": self.COLOR_ANALYTICS,
            "fields": [
                {
                    "name": "Detection Rate",
                    "value": f"{detection_rate:.1f}%",
                    "inline": True
                },
                {
                    "name": "Invocation Success Rate",
                    "value": f"{invocation_success_rate * 100:.1f}%",
                    "inline": True
                },
                {
                    "name": "Fallback Rate",
                    "value": f"{fallback_rate:.1f}%",
                    "inline": True
                },
                {
                    "name": "Avg Discovery Time",
                    "value": f"{avg_discovery_time_ms:.0f}ms",
                    "inline": True
                },
                {
                    "name": "Performance Improvement",
                    "value": f"{performance_improvement_factor:.1f}x faster",
                    "inline": True
                },
                {
                    "name": "Status",
                    "value": "✅ VOIX operational" if detection_rate > 0 else "⚠️ No VOIX-enabled sites detected",
                    "inline": False
                }
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        await self._send("metrics", embed, level=2)

    async def voix_site_available_alert(self, url: str, tools_found: int) -> None:
        """
        Alert when a VOIX-enabled site becomes available.
        
        Args:
            url: URL of VOIX-enabled site
            tools_found: Number of VOIX tools found
        """
        embed = {
            "title": "🎉 New VOIX-Enabled Site Detected!",
            "description": f"**{url}** now supports VOIX declarative automation.",
            "color": self.COLOR_SUCCESS,
            "fields": [
                {
                    "name": "URL",
                    "value": url,
                    "inline": False
                },
                {
                    "name": "Tools Found",
                    "value": str(tools_found),
                    "inline": True
                },
                {
                    "name": "Status",
                    "value": "✅ Ready for VOIX automation",
                    "inline": True
                }
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        await self._send("alerts", embed, level=2)

    async def daily_report(self, statistics: Dict[str, Any]) -> None:
        # Extract VOIX metrics if available
        voix_metrics = statistics.get("voix_metrics", {})
        voix_detection_rate = voix_metrics.get("detection_rate", 0.0)
        voix_invocation_success_rate = voix_metrics.get("invocation_success_rate", 0.0)
        voix_fallback_rate = voix_metrics.get("fallback_rate", 0.0)
        
        # Build description with VOIX metrics
        description = (
            f"**Businesses Built:** {statistics.get('businesses_built', 0)}\n"
            f"**Success Rate:** {statistics.get('success_rate', 0)}%\n"
            f"**Avg Quality:** {statistics.get('avg_quality_score', 0)}/100\n"
            f"**Total Revenue:** ${statistics.get('total_revenue', 0):.2f}\n"
            f"**Active Businesses:** {statistics.get('active_businesses', 0)}"
        )
        
        # Add VOIX metrics if available
        if voix_metrics:
            description += (
                f"\n\n**VOIX Metrics (Integration #74):**\n"
                f"**Detection Rate:** {voix_detection_rate:.1f}%\n"
                f"**Invocation Success:** {voix_invocation_success_rate * 100:.1f}%\n"
                f"**Fallback Rate:** {voix_fallback_rate:.1f}%"
            )
        
        await self._send(
            "metrics",
            self._embed(
                title="📊 Daily Report",
                description=description,
                color=self.COLOR_ANALYTICS,
            ),
            level=4,
        )
    async def _flush_progress_buffer(self, business_id: str, agent_name: str) -> None:
        key = (business_id, agent_name)
        buffer = self._progress_buffer.pop(key, None)
        if not buffer:
            return
        description = "\n".join(f"- {line}" for line in buffer)
        await self._send(
            "dashboard",
            self._embed(
                title=f"📝 {agent_name} Progress",
                description=description,
                color=self.COLOR_PROGRESS,
                footer=f"Agent: {agent_name} • Business: {business_id}",
            ),
            level=3,
            agent_name=agent_name,
        )


# Convenience synchronous API -------------------------------------------------

def fire_and_forget(coro: Awaitable[None]) -> None:
    """Utility used by legacy synchronous code paths."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
    else:
        loop.create_task(coro)

