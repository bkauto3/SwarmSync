"""
EMAIL AGENT - Microsoft Agent Framework Version
Version: 4.1 (Enhanced with DAAO + TUMIX + AP2 Payments)

Handles email campaigns, automation, and deliverability.
AP2 Integration: Supports SendGrid/Mailgun, email validation, and Customer.io automation
"""

import asyncio
import json
import logging
import threading
import hmac
import hashlib
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Optional, Any
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
# Import AP2 Service for payment integrations
from infrastructure.ap2_service import AP2Service
from infrastructure.x402_vendor_cache import get_x402_vendor_cache
from infrastructure.x402_client import get_x402_client, X402PaymentError

logger = logging.getLogger(__name__)


class EmailAgent:
    """Email campaign and automation agent with AP2 payment integration"""

    def __init__(self, business_id: str = "default"):
        self.business_id = business_id
        self.agent = None

        # Initialize DAAO router for cost optimization
        self.router = get_daao_router()

        # Initialize TUMIX for iterative refinement
        self.termination = get_tumix_termination(
            min_rounds=2,
            max_rounds=4,
            improvement_threshold=0.05
        )

        # Initialize AP2 Service for payment integrations
        self.ap2_service = AP2Service()
        self._ap2_loop = None
        self._ap2_thread = None

        # AP2 Budget tracking
        self._monthly_limit = 200.0  # $200/month default for email
        self._current_monthly_spend = 0.0
        self._budget_window = datetime.utcnow().strftime("%Y-%m")
        self._ap2_secret = self._generate_ap2_secret()

        # Track refinement sessions for metrics
        self.refinement_history: List[List[RefinementResult]] = []

        # Email-specific audit trail and cost tracking
        self.email_alerts: List[Dict[str, Any]] = []
        self.email_audit_log: List[Dict[str, Any]] = []
        self.tool_spend: Dict[str, float] = defaultdict(float)
        self.vendor_cache = get_x402_vendor_cache()
        self.x402_client = get_x402_client()

        logger.info(f"EmailAgent v4.1 initialized with DAAO + TUMIX + AP2 for business: {business_id}")
        self._start_ap2_loop()

    def _generate_ap2_secret(self) -> str:
        """Generate AP2 secret for signature verification"""
        import secrets
        return secrets.token_urlsafe(32)

    def _check_monthly_budget(self, amount: float) -> None:
        """Check if transaction would exceed monthly budget"""
        current_month = datetime.utcnow().strftime("%Y-%m")
        if current_month != self._budget_window:
            # New month - reset spend
            self._current_monthly_spend = 0.0
            self._budget_window = current_month

        if self._current_monthly_spend + amount > self._monthly_limit:
            raise ValueError(
                f"Transaction ${amount} would exceed monthly budget. "
                f"Current spend: ${self._current_monthly_spend}, Limit: ${self._monthly_limit}"
            )

    def _sign_audit_entry(self, entry: Dict[str, Any]) -> str:
        """Create HMAC signature for audit trail entry"""
        message = json.dumps(entry, sort_keys=True, default=str)
        signature = hmac.new(
            self._ap2_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _record_audit_log(
        self,
        action: str,
        service: str,
        price: float,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record audit trail entry with signature"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "service": service,
            "price": price,
            "status": status,
            "metadata": metadata or {}
        }
        entry["signature"] = self._sign_audit_entry(entry)
        self.email_audit_log.append(entry)
        self.tool_spend[service] += price
        self._current_monthly_spend += price
        logger.info(f"Email audit: {action} {service} ${price} [{status}]")

    async def initialize(self):
        cred = AzureCliCredential()
        client = AzureAIAgentClient(async_credential=cred)
        self.agent = ChatAgent(
            chat_client=client,
            instructions="You are an email marketing specialist. Design email campaigns, manage subscriber lists, optimize deliverability, create automated sequences, and analyze campaign performance. Follow email best practices, ensure CAN-SPAM compliance, and maintain high engagement rates. Use A/B testing to optimize subject lines and content. Leverage AP2 integration for SendGrid/Mailgun sending, email validation, and Customer.io automation.",
            name="email-agent",
            tools=[self.create_campaign, self.send_email, self.segment_audience, self.track_campaign_metrics, self.optimize_deliverability, self.validate_emails, self.setup_automation]
        )
        print(f"✉️ Email Agent v4.1 initialized for business: {self.business_id}")

    def create_campaign(self, campaign_name: str, subject_line: str, target_segment: str) -> str:
        """Create a new email campaign"""
        x402_receipt = self._charge_x402(
            vendor="email-content-llm",
            amount=max(0.02, len(subject_line) / 1000),
            metadata={"campaign": campaign_name, "segment": target_segment},
        )
        result = {
            "campaign_id": f"CAMP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "campaign_name": campaign_name,
            "subject_line": subject_line,
            "target_segment": target_segment,
            "estimated_recipients": 15678,
            "send_time": "optimal",
            "status": "draft",
            "ab_test_enabled": True,
            "created_at": datetime.now().isoformat(),
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def send_email(
        self,
        campaign_id: str,
        recipients: List[str],
        send_immediately: bool,
        sendgrid_cost: float = 0.0,
        mailgun_cost: float = 0.0
    ) -> str:
        """Send an email campaign to recipients with AP2 approval integration

        Args:
            campaign_id: Campaign identifier
            recipients: List of recipient email addresses
            send_immediately: Whether to send now or schedule
            sendgrid_cost: Estimated SendGrid cost (optional)
            mailgun_cost: Estimated Mailgun cost (optional)

        Returns:
            JSON result with AP2 approvals and send status
        """
        ap2_approvals = []
        total_cost = 0.0
        x402_receipt = self._charge_x402(
            vendor="email-delivery-api",
            amount=max(0.03, len(recipients) * 0.0005),
            metadata={"campaign_id": campaign_id, "recipients": len(recipients)},
        )

        # Determine sending service and cost
        if len(recipients) > 1000:
            service_name = "SendGrid subscription"
            service_cost = sendgrid_cost or 15.0  # $15/month base
        else:
            service_name = "Mailgun subscription"
            service_cost = mailgun_cost or 0.0  # Free tier

        if service_cost > 0:
            approval = self._request_email_service(
                service_name=service_name,
                price=service_cost,
                metadata={"recipients": len(recipients), "campaign_id": campaign_id},
            )
            ap2_entry = {
                "service": service_name,
                "price": service_cost,
                "status": approval.get("status", "pending"),
                "auto_approval": service_cost <= 20.0,
                "manual_review": service_cost > 20.0,
                "batch_approval": approval.get("batch_approval"),
                "intent": approval.get("intent"),
                "cart": approval.get("cart"),
            }
            ap2_approvals.append(ap2_entry)
            total_cost += service_cost

        # Alert if total cost is significant
        if total_cost > 50.0:
            alert = {
                "timestamp": datetime.now().isoformat(),
                "type": "high_cost_alert",
                "cost": total_cost,
                "threshold": 50.0,
                "campaign_id": campaign_id
            }
            self.email_alerts.append(alert)
            logger.warning(f"High cost alert: ${total_cost} for campaign {campaign_id}")

        result = {
            "send_id": f"SEND-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "campaign_id": campaign_id,
            "recipients_count": len(recipients),
            "send_immediately": send_immediately,
            "scheduled_time": None if send_immediately else datetime.now().isoformat(),
            "estimated_delivery_time_minutes": 5,
            "status": "sending" if send_immediately else "scheduled",
            "total_cost": total_cost,
            "ap2_approvals": ap2_approvals,
            "sent_at": datetime.now().isoformat(),
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def segment_audience(self, criteria: Dict[str, str], segment_name: str) -> str:
        """Create audience segment based on criteria"""
        x402_receipt = self._charge_x402(
            vendor="email-segmentation-api",
            amount=max(0.02, len(criteria) * 0.005),
            metadata={"segment": segment_name},
        )
        result = {
            "segment_id": f"SEG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "segment_name": segment_name,
            "criteria": criteria,
            "matched_contacts": 3456,
            "percentage_of_total": 22.5,
            "avg_engagement_score": 7.8,
            "created_at": datetime.now().isoformat(),
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def track_campaign_metrics(self, campaign_id: str) -> str:
        """Track performance metrics for an email campaign"""
        x402_receipt = self._charge_x402(
            vendor="email-analytics-api",
            amount=0.02,
            metadata={"campaign_id": campaign_id},
        )
        result = {
            "campaign_id": campaign_id,
            "metrics": {
                "sent": 15678,
                "delivered": 15456,
                "opened": 4623,
                "clicked": 1234,
                "bounced": 222,
                "unsubscribed": 45,
                "spam_reports": 3,
                "open_rate": 29.9,
                "click_rate": 26.7,
                "click_to_open_rate": 8.0,
                "bounce_rate": 1.4,
                "unsubscribe_rate": 0.29
            },
            "revenue_generated": 12456.78,
            "tracked_at": datetime.now().isoformat(),
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def optimize_deliverability(self, domain: str) -> str:
        """Analyze and optimize email deliverability"""
        x402_receipt = self._charge_x402(
            vendor="email-deliverability-scan",
            amount=max(0.02, len(domain) * 0.001),
            metadata={"domain": domain},
        )
        result = {
            "analysis_id": f"DELIV-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "domain": domain,
            "deliverability_score": 92.5,
            "sender_reputation": 88,
            "authentication": {
                "spf": "pass",
                "dkim": "pass",
                "dmarc": "pass"
            },
            "recommendations": [
                "Implement double opt-in for new subscribers",
                "Clean list of inactive subscribers (6+ months)",
                "Reduce sending frequency to re-engage dormant contacts",
                "Add plain text version to all emails",
                "Review content for spam trigger words"
            ],
            "blacklist_status": "clean",
            "analyzed_at": datetime.now().isoformat(),
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)


    def validate_emails(self, email_list: List[str], validation_service: str = "ZeroBounce") -> str:
        """Validate email addresses with AP2 approval

        Args:
            email_list: List of emails to validate
            validation_service: Service to use for validation

        Returns:
            JSON result with validation stats and AP2 approvals
        """
        ap2_approvals = []

        # Estimate validation cost: $0.004-0.01 per email
        cost_per_email = 0.004  # Minimum cost
        total_validation_cost = len(email_list) * cost_per_email
        x402_receipt = self._charge_x402(
            vendor="email-validation-api",
            amount=max(0.02, len(email_list) * 0.0002),
            metadata={"count": len(email_list), "service": validation_service},
        )

        try:
            # Check monthly budget
            self._check_monthly_budget(total_validation_cost)

            # Create AP2 approval
            approval = {
                "service": f"{validation_service} email validation",
                "price": total_validation_cost,
                "currency": "USD",
                "auto_approval": total_validation_cost <= 10.0,
                "manual_review": total_validation_cost > 10.0,
                "category": "email_validation",
                "description": f"Validate {len(email_list)} email addresses",
                "timestamp": datetime.now().isoformat(),
                "approval_id": f"AP2-VAL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }

            ap2_approvals.append(approval)

            # Record audit trail
            self._record_audit_log(
                action="validate_emails",
                service=f"{validation_service} email validation",
                price=total_validation_cost,
                status="pending_approval",
                metadata={"email_count": len(email_list)}
            )

            logger.info(f"Email validation approval requested: {len(email_list)} emails, ${total_validation_cost}")

        except ValueError as e:
            logger.error(f"Budget check failed for validation: {e}")
            raise

        # Simulate validation results
        valid_count = int(len(email_list) * 0.92)  # 92% valid rate
        invalid_count = len(email_list) - valid_count

        result = {
            "validation_id": f"VAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "service": validation_service,
            "total_emails": len(email_list),
            "valid_emails": valid_count,
            "invalid_emails": invalid_count,
            "valid_rate": (valid_count / len(email_list) * 100) if email_list else 0,
            "total_cost": total_validation_cost,
            "ap2_approvals": ap2_approvals,
            "timestamp": datetime.now().isoformat(),
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def setup_automation(
        self,
        automation_name: str,
        trigger_type: str,
        workflow_steps: int,
        automation_platform: str = "Customer.io"
    ) -> str:
        """Setup email automation workflow with AP2 approval

        Args:
            automation_name: Name of automation workflow
            trigger_type: Type of trigger (e.g., 'on_signup', 'on_purchase')
            workflow_steps: Number of workflow steps
            automation_platform: Platform to use (default: Customer.io)

        Returns:
            JSON result with automation setup and AP2 approvals
        """
        ap2_approvals = []

        # Customer.io pricing: $50-499/month based on contacts
        # Estimate: $99/month for mid-tier
        automation_cost = 99.0
        x402_receipt = self._charge_x402(
            vendor="email-automation-api",
            amount=max(0.03, workflow_steps * 0.002),
            metadata={"automation_name": automation_name},
        )

        try:
            # Check monthly budget
            self._check_monthly_budget(automation_cost)

            # Create AP2 approval
            approval = {
                "service": f"{automation_platform} automation platform",
                "price": automation_cost,
                "currency": "USD",
                "auto_approval": False,  # Always manual review for automation setup
                "manual_review": True,
                "category": "automation_platform",
                "description": f"Setup {automation_name} automation with {workflow_steps} steps",
                "timestamp": datetime.now().isoformat(),
                "approval_id": f"AP2-AUTO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }

            ap2_approvals.append(approval)

            # Record audit trail
            self._record_audit_log(
                action="setup_automation",
                service=f"{automation_platform} automation platform",
                price=automation_cost,
                status="pending_approval",
                metadata={
                    "automation_name": automation_name,
                    "trigger_type": trigger_type,
                    "workflow_steps": workflow_steps
                }
            )

            logger.info(f"Automation setup approval requested: {automation_name}, ${automation_cost}")

        except ValueError as e:
            logger.error(f"Budget check failed for automation: {e}")
            raise

        result = {
            "automation_id": f"AUTO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "automation_name": automation_name,
            "platform": automation_platform,
            "trigger_type": trigger_type,
            "workflow_steps": workflow_steps,
            "status": "pending_setup",
            "monthly_cost": automation_cost,
            "ap2_approvals": ap2_approvals,
            "estimated_activation": "24 hours",
            "timestamp": datetime.now().isoformat(),
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

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
            'id': f'email-{{datetime.now().strftime("%Y%m%d%H%M%S")}}',
            'description': task_description,
            'priority': priority,
            'required_tools': []
        }

        decision = self.router.route_task(task, budget_conscious=True)

        logger.info(
            f"Task routed: {decision.reasoning}",
            extra={
                'agent': 'EmailAgent',
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
                'agent': 'EmailAgent',
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
            'agent': 'EmailAgent',
            'tumix_sessions': tumix_savings['sessions'],
            'tumix_baseline_rounds': tumix_savings['baseline_rounds'],
            'tumix_actual_rounds': tumix_savings['tumix_rounds'],
            'tumix_savings_percent': tumix_savings['savings_percent'],
            'tumix_total_saved': tumix_savings['savings'],
            'daao_info': 'DAAO routing automatically applied to all tasks'
        }

    def _request_email_service(
        self,
        *,
        service_name: str,
        price: float,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        self._check_monthly_budget(price)
        purchase_callable = getattr(
            self.ap2_service, "safe_request_purchase", self.ap2_service.request_purchase
        )
        approval = self._execute_ap2_coro(
            purchase_callable(
                agent_name="email_agent",
                user_id=f"{self.business_id or 'email'}_owner",
                service_name=service_name,
                price=price,
                categories=["email_infrastructure"],
                metadata=metadata,
            )
        )
        self._record_audit_log(
            action="send_email",
            service=service_name,
            price=price,
            status=approval.get("status", "pending"),
            metadata=metadata,
        )
        logger.info(f"Email send approval requested: {service_name} ${price}")
        return approval

    def _charge_x402(
        self,
        vendor: str,
        amount: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            prepared_metadata = self._prepare_x402_metadata(vendor, metadata)
            receipt = self.x402_client.record_manual_payment(
                agent_name="email_agent",
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
            raise RuntimeError(f"Email Agent x402 budget exceeded: {exc}") from exc

    def _prepare_x402_metadata(
        self, vendor: str, metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        data = dict(metadata or {})
        data.setdefault("business_id", self.business_id)
        data.setdefault("agent_name", "email_agent")
        data.setdefault("category", "email")
        capabilities = self.vendor_cache.lookup(vendor)
        if capabilities:
            data.setdefault("accepted_tokens", capabilities.get("accepted_tokens"))
            data.setdefault("preferred_chain", capabilities.get("preferred_chain"))
        return data

    def _start_ap2_loop(self) -> None:
        if self._ap2_loop:
            return
        try:
            self._ap2_loop = asyncio.new_event_loop()
            self._ap2_thread = threading.Thread(
                target=self._run_ap2_loop,
                name="EmailAgent-AP2Loop",
                daemon=True,
            )
            self._ap2_thread.start()
        except Exception as exc:
            logger.warning("AP2 loop unavailable: %s", exc)
            self._ap2_loop = None
            self._ap2_thread = None

    def _run_ap2_loop(self) -> None:
        if not self._ap2_loop:
            return
        asyncio.set_event_loop(self._ap2_loop)
        self._ap2_loop.run_forever()

    def _stop_ap2_loop(self) -> None:
        if self._ap2_loop:
            self._ap2_loop.call_soon_threadsafe(self._ap2_loop.stop)
        if self._ap2_thread:
            self._ap2_thread.join(timeout=1)
        self._ap2_loop = None
        self._ap2_thread = None

    def _execute_ap2_coro(self, coro: Any) -> Dict[str, Any]:
        if not self._ap2_loop:
            return asyncio.run(coro)
        future = asyncio.run_coroutine_threadsafe(coro, self._ap2_loop)
        try:
            return future.result(timeout=30)
        except asyncio.TimeoutError as exc:
            logger.error("AP2 request timed out: %s", exc, exc_info=True)
            raise RuntimeError("AP2 request timed out") from exc
        except Exception as exc:  # noqa: BLE001
            logger.error("AP2 request failed: %s", exc, exc_info=True)
            raise RuntimeError("AP2 request failed") from exc

    def shutdown(self) -> None:
        """Clean up threaded resources."""
        self._stop_ap2_loop()



async def get_email_agent(business_id: str = "default") -> EmailAgent:
    agent = EmailAgent(business_id=business_id)
    await agent.initialize()
    return agent
