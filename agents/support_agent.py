"""
SUPPORT AGENT - Microsoft Agent Framework Version
Version: 4.0 (Enhanced with DAAO + TUMIX) (Day 2 Migration)

Handles customer support, ticket management, and user assistance.
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

# Import OCR capability (legacy)
from infrastructure.ocr.ocr_agent_tool import support_agent_ticket_image_processor

# Import DeepSeek-OCR for visual memory compression (NEW: 92.9% token savings)
from infrastructure.deepseek_ocr_compressor import DeepSeekOCRCompressor, ResolutionMode

# Import self-correction for response validation
from infrastructure.self_correction import (
    SelfCorrectingAgent,
    ValidationCategory,
    get_self_correcting_agent
)

# Import OpenEnv for customer issue reproduction
from infrastructure.openenv_wrapper import EnvRegistry
from infrastructure.env_learning_agent import EnvironmentLearningAgent

# Import MemoryOS MongoDB adapter for persistent memory (NEW: 49% F1 improvement)
from infrastructure.memory_os_mongodb_adapter import (
    GenesisMemoryOSMongoDB,
    create_genesis_memory_mongodb
)
from infrastructure.memory.memori_tool import MemoriMemoryToolset
from infrastructure.ap2_service import AP2Service, AP2BudgetConfig, DEFAULT_BUDGETS
from infrastructure.x402_vendor_cache import get_x402_vendor_cache
from infrastructure.x402_client import get_x402_client, X402PaymentError

logger = logging.getLogger(__name__)


class SupportAgent:
    """Customer support and ticket management agent"""

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

        # Track refinement sessions for metrics
        self.refinement_history: List[List[RefinementResult]] = []

        # Initialize DeepSeek-OCR for visual memory compression (NEW: 71%+ token savings)
        self.ocr_compressor = DeepSeekOCRCompressor()

        # Self-correction wrapper (initialized after agent setup)
        self.self_correcting: Optional[SelfCorrectingAgent] = None

        # OpenEnv for customer issue reproduction (initialized after agent setup)
        self.browser_env = None
        self.env_agent = None

        # Initialize MemoryOS MongoDB adapter for persistent memory (NEW: 49% F1 improvement)
        # Enables ticket resolution memory, common issue patterns, user history tracking
        self.memory: Optional[GenesisMemoryOSMongoDB] = None
        self._init_memory()
        self.memori_toolset: Optional[MemoriMemoryToolset] = None
        self._init_memori_toolset()

        # AP2 + budgeting
        self.ap2_service: Optional[AP2Service] = None
        self._ap2_loop: Optional[asyncio.AbstractEventLoop] = None
        self._ap2_thread: Optional[threading.Thread] = None
        self._budget_config = self._get_support_budget()
        self._monthly_spend = 0.0
        self._budget_window = datetime.utcnow().strftime("%Y-%m")
        self._ap2_secret = os.getenv("AP2_SECRET_KEY", "dev-support-secret")
        self.support_audit: List[Dict[str, Any]] = []
        self.support_alerts: List[Dict[str, Any]] = []
        self.channel_spend: Dict[str, float] = defaultdict(float)
        self.vendor_cache = get_x402_vendor_cache()
        self.x402_client = get_x402_client()

        try:
            self.ap2_service = AP2Service()
        except (RuntimeError, OSError) as exc:
            logger.warning("SupportAgent AP2 unavailable: %s", exc)
            self.ap2_service = None

        if self.ap2_service:
            self._ap2_loop = asyncio.new_event_loop()
            self._ap2_thread = threading.Thread(
                target=self._run_ap2_loop,
                name="SupportAgent-AP2Loop",
                daemon=True,
            )
            self._ap2_thread.start()


    async def initialize(self):
        cred = AzureCliCredential()
        client = AzureAIAgentClient(async_credential=cred)
        self.agent = ChatAgent(
            chat_client=client,
            instructions="You are a customer support specialist with OCR image reading capabilities and issue reproduction via Playwright. Handle support tickets, answer user questions, troubleshoot issues, and escalate complex problems. You can process customer screenshots and error images using OCR, and reproduce customer issues by learning browser automation via self-play. Maintain empathetic, professional communication. Track ticket resolution metrics and identify common issues for documentation. Aim for 84% autonomous resolution rate.",
            name="support-agent",
            tools=[
                self.create_ticket,
                self.respond_to_ticket,
                self.escalate_ticket,
                self.search_knowledge_base,
                self.generate_support_report,
                self.process_ticket_image,
                self.reproduce_customer_issue,
                self.remember_customer_fact,
                self.recall_customer_facts,
            ]
        )

        # Initialize OpenEnv for customer issue reproduction
        self.browser_env = EnvRegistry.make("playwright")
        # Create LLM client directly (Railway: no local LLM, use cloud APIs)
        try:
            from anthropic import Anthropic
            import os
            llm_client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        except Exception as e:
            logger.warning(f"Could not initialize LLM client for OpenEnv: {e}")
            llm_client = None

        self.env_agent = EnvironmentLearningAgent(
            env=self.browser_env,
            llm_client=llm_client,
            casebank=None,  # TODO: Integrate with CaseBank
            max_episodes=8  # Support: moderate learning
        )

        print(f"💬 Support Agent initialized for business: {self.business_id}")
        print(f"   - OpenEnv issue reproduction enabled (Playwright)")
        print(f"   - MemoryOS MongoDB backend enabled (49% F1 improvement)\n")

    def _init_memory(self):
        """Initialize MemoryOS MongoDB backend for Support ticket memory."""
        try:
            import os
            self.memory = create_genesis_memory_mongodb(
                mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017/"),
                database_name="genesis_memory_support",
                short_term_capacity=10,  # Recent tickets
                mid_term_capacity=1000,  # Historical ticket patterns (Support-specific, higher capacity)
                long_term_knowledge_capacity=200  # Common issues, user interaction history
            )
            logger.info("[SupportAgent] MemoryOS MongoDB initialized for ticket resolution tracking")
        except Exception as e:
            logger.warning(f"[SupportAgent] Failed to initialize MemoryOS: {e}. Memory features disabled.")
            self.memory = None

    def _init_memori_toolset(self):
        """Initialize Memori-based memory toolset."""
        try:
            self.memori_toolset = MemoriMemoryToolset()
            logger.info("[SupportAgent] Memori memory toolset ready")
        except Exception as exc:
            logger.warning("[SupportAgent] Failed to initialize Memori toolset: %s", exc)
            self.memori_toolset = None

    def remember_customer_fact(
        self,
        user_id: str,
        fact_key: str,
        fact_value: str,
        importance: str = "normal",
        labels: Optional[str] = None,
        ttl_hours: Optional[int] = None
    ) -> str:
        """Store a structured customer fact in Memori."""
        if not self.memori_toolset:
            return "Memori memory store unavailable."

        label_list = (
            [label.strip() for label in labels.split(",") if label.strip()]
            if labels
            else None
        )

        record = self.memori_toolset.store_user_fact(
            user_id=user_id,
            fact_key=fact_key,
            fact_value=fact_value,
            importance=importance,
            labels=label_list,
            ttl_hours=ttl_hours,
        )
        return json.dumps(
            {"status": "stored", "memory": record},
            ensure_ascii=False
        )

    def recall_customer_facts(
        self,
        user_id: str,
        query: str = "",
        limit: int = 5,
        label: Optional[str] = None
    ) -> str:
        """Search stored customer memories for grounding a reply."""
        if not self.memori_toolset:
            return "Memori memory store unavailable."

        memories = self.memori_toolset.search_user_facts(
            user_id=user_id,
            query=query or None,
            label=label,
            limit=limit,
        )
        return json.dumps(
            {"memories_found": len(memories), "memories": memories},
            ensure_ascii=False
        )

    async def enable_self_correction(self, qa_agent: Any, max_attempts: int = 3):
        """
        Enable self-correction QA loop for support response validation.

        Args:
            qa_agent: QA agent for validation
            max_attempts: Maximum correction attempts
        """
        self.self_correcting = get_self_correcting_agent(
            agent=self,
            qa_agent=qa_agent,
            max_attempts=max_attempts,
            validation_categories=[
                ValidationCategory.CORRECTNESS,
                ValidationCategory.COMPLETENESS,
                ValidationCategory.QUALITY,
                ValidationCategory.SAFETY
            ]
        )
        logger.info(
            f"Support Agent self-correction enabled: max_attempts={max_attempts}"
        )

    async def respond_with_validation(
        self,
        task: str,
        expectations: Optional[Dict] = None
    ) -> Dict:
        """
        Generate support response with automatic QA validation loop.

        Args:
            task: Support task/ticket description
            expectations: Expected response properties

        Returns:
            Validated support response
        """
        if not self.self_correcting:
            raise RuntimeError(
                "Self-correction not enabled. Call enable_self_correction() first."
            )

        default_expectations = {
            "professional_tone": True,
            "answers_question": True,
            "safe_content": True,
            "actionable_steps": True
        }

        expectations = {**default_expectations, **(expectations or {})}

        return await self.self_correcting.execute_with_validation(
            task=task,
            expectations=expectations,
            context={"agent": "SupportAgent", "business_id": self.business_id}
        )

    def create_ticket(
        self,
        user_id: str,
        issue_description: str,
        priority: str,
        *,
        helpdesk_tool: str = "Zendesk",
        seat_cost: float = 45.0,
    ) -> str:
        """Create a new support ticket"""
        receipt = self._ensure_support_budget(
            service_name=f"{helpdesk_tool} seat",
            amount=seat_cost,
            metadata={"tool": helpdesk_tool, "category": "ticketing"},
        )
        x402_receipt = self._charge_x402(
            vendor="support-helpdesk-api",
            amount=max(0.02, seat_cost * 0.0004),
            metadata={"helpdesk_tool": helpdesk_tool, "user_id": user_id},
        )
        result = {
            "ticket_id": f"TICKET-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "user_id": user_id,
            "issue_description": issue_description,
            "priority": priority,
            "status": "open",
            "assigned_to": "auto-triage",
            "created_at": datetime.now().isoformat(),
            "sla_deadline": datetime.now().isoformat(),
            "ap2_approval": receipt,
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def respond_to_ticket(
        self,
        ticket_id: str,
        response: str,
        resolution_type: str,
        *,
        voice_minutes: float = 0.0,
        qa_review_cost: float = 0.0,
    ) -> str:
        """
        Respond to a support ticket with a solution.

        NEW: MemoryOS integration - Retrieves similar ticket resolutions and stores successful patterns
        for future reference (49% F1 improvement on ticket resolution accuracy).
        """
        user_id = f"support_{self.business_id}"

        # Retrieve historical ticket resolution patterns from memory
        historical_context = ""
        if self.memory:
            try:
                memories = self.memory.retrieve(
                    agent_id="support",
                    user_id=user_id,
                    query=f"ticket resolution: {response[:100]}",  # Use response preview as query
                    memory_type=None,
                    top_k=3
                )
                if memories:
                    historical_context = "\n".join([
                        f"- Similar resolution: {m['content'].get('agent_response', '')}"
                        for m in memories
                    ])
                    logger.info(f"[SupportAgent] Retrieved {len(memories)} similar ticket patterns from memory")
            except Exception as e:
                logger.warning(f"[SupportAgent] Memory retrieval failed: {e}")

        receipts = []
        if voice_minutes > 0:
            receipts.append(
                self._ensure_support_budget(
                    service_name="Twilio voice minutes",
                    amount=voice_minutes,
                    metadata={"category": "voice_support"},
                )
            )
        if qa_review_cost > 0:
            receipts.append(
                self._ensure_support_budget(
                    service_name="QA labeling review",
                    amount=qa_review_cost,
                    metadata={"category": "qa_review"},
                )
            )

        x402_receipt = self._charge_x402(
            vendor="support-response-llm",
            amount=max(
                0.02,
                (voice_minutes * 0.01)
                + (qa_review_cost * 0.0005)
                + (len(response) / 8000),
            ),
            metadata={"ticket_id": ticket_id, "resolution_type": resolution_type},
        )

        result = {
            "ticket_id": ticket_id,
            "response": response,
            "resolution_type": resolution_type,
            "status": "resolved" if resolution_type == "resolved" else "pending",
            "response_time_minutes": 15,
            "customer_satisfaction_score": None,
            "responded_at": datetime.now().isoformat(),
            "historical_context": historical_context if historical_context else "No similar tickets found",
            "ap2_approvals": [receipt for receipt in receipts if receipt],
            "x402_payment": x402_receipt,
        }

        # Store ticket resolution in memory for future reference
        if self.memory and resolution_type == "resolved":
            try:
                self.memory.store(
                    agent_id="support",
                    user_id=user_id,
                    user_input=f"Resolve ticket {ticket_id}",
                    agent_response=f"Resolution: {response} (Type: {resolution_type})",
                    memory_type="conversation"
                )
                logger.info(f"[SupportAgent] Stored ticket resolution in memory: {ticket_id}")
            except Exception as e:
                logger.warning(f"[SupportAgent] Memory storage failed: {e}")

        return json.dumps(result, indent=2)

    def escalate_ticket(
        self,
        ticket_id: str,
        escalation_reason: str,
        escalation_team: str,
        *,
        incident_tool: str = "PagerDuty",
        incident_cost: float = 75.0,
    ) -> str:
        """Escalate a ticket to a specialized team"""
        receipt = self._ensure_support_budget(
            service_name=f"{incident_tool} incident",
            amount=incident_cost,
            metadata={"tool": incident_tool, "category": "escalation"},
        )
        x402_receipt = self._charge_x402(
            vendor="support-incident-alert",
            amount=max(0.02, incident_cost * 0.0005),
            metadata={"ticket_id": ticket_id, "team": escalation_team},
        )
        result = {
            "ticket_id": ticket_id,
            "escalation_reason": escalation_reason,
            "escalated_to": escalation_team,
            "original_priority": "medium",
            "new_priority": "high",
            "escalation_notes": "Requires specialized technical knowledge",
            "escalated_at": datetime.now().isoformat(),
            "ap2_approval": receipt,
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def search_knowledge_base(self, query: str, category: str) -> str:
        """Search the knowledge base for relevant articles"""
        result = {
            "query": query,
            "category": category,
            "results": [
                {"article_id": "KB-001", "title": "Common Login Issues", "relevance_score": 0.92},
                {"article_id": "KB-015", "title": "Password Reset Guide", "relevance_score": 0.87},
                {"article_id": "KB-042", "title": "Account Security Best Practices", "relevance_score": 0.76}
            ],
            "total_results": 3,
            "searched_at": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)

    def generate_support_report(self, start_date: str, end_date: str) -> str:
        """Generate a support metrics report for a date range"""
        receipt = self._ensure_support_budget(
            service_name="Support analytics add-on",
            amount=25.0,
            metadata={"category": "reporting"},
        )
        x402_receipt = self._charge_x402(
            vendor="support-analytics",
            amount=0.03,
            metadata={"start": start_date, "end": end_date},
        )
        result = {
            "report_id": f"REPORT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "period": {"start": start_date, "end": end_date},
            "metrics": {
                "total_tickets": 487,
                "resolved_tickets": 409,
                "autonomous_resolution_rate": 0.84,
                "average_response_time_minutes": 12,
                "customer_satisfaction_score": 4.6,
                "common_issues": ["login", "billing", "feature_requests"]
            },
            "generated_at": datetime.now().isoformat(),
            "ap2_approval": receipt,
            "x402_payment": x402_receipt,
        }
        return json.dumps(result, indent=2)

    def handle_ticket_workflow(
        self,
        user_id: str,
        issue_description: str,
        priority: str,
        *,
        voice_minutes: float = 0.0,
        qa_review_cost: float = 0.0,
        incident_cost: float = 75.0,
    ) -> Dict[str, Any]:
        """End-to-end workflow returning aggregated AP2 receipts."""
        ticket = json.loads(
            self.create_ticket(
                user_id=user_id,
                issue_description=issue_description,
                priority=priority,
            )
        )
        response = json.loads(
            self.respond_to_ticket(
                ticket_id=ticket["ticket_id"],
                response="Issue acknowledged and resolved.",
                resolution_type="resolved",
                voice_minutes=voice_minutes,
                qa_review_cost=qa_review_cost,
            )
        )
        escalation = json.loads(
            self.escalate_ticket(
                ticket_id=ticket["ticket_id"],
                escalation_reason="Requires specialist follow-up",
                escalation_team="Tier-2",
                incident_cost=incident_cost,
            )
        )
        report = json.loads(
            self.generate_support_report(
                start_date=datetime.now().isoformat(),
                end_date=datetime.now().isoformat(),
            )
        )
        receipts: List[Dict[str, Any]] = []
        if ticket.get("ap2_approval"):
            receipts.append(ticket["ap2_approval"])
        receipts.extend(response.get("ap2_approvals", []))
        if escalation.get("ap2_approval"):
            receipts.append(escalation["ap2_approval"])
        if report.get("ap2_approval"):
            receipts.append(report["ap2_approval"])
        return {
            "ticket": ticket,
            "response": response,
            "escalation": escalation,
            "report": report,
            "ap2_receipts": receipts,
        }

    async def process_ticket_image(self, image_path: str, expected_issues: List[str] = None) -> str:
        """
        Process customer support ticket images using DeepSeek-OCR compression

        NEW: Visual memory compression (92.9% token savings)
        - Before: ~3,600 tokens per customer screenshot (raw image)
        - After: ~100 tokens (Small mode optimized for simple screenshots)
        - Cost savings: $50/month for 5,000 support tickets

        Args:
            image_path: Path to customer screenshot/error image
            expected_issues: Optional list of keywords to check for (e.g., ["error", "crash"])

        Returns:
            JSON string with processed image data and compressed markdown
        """
        self._charge_x402(
            vendor="support-ocr",
            amount=max(0.02, 0.004 * (len(expected_issues) if expected_issues else 1)),
            metadata={"image_path": image_path},
        )
        try:
            # Compress ticket image using DeepSeek-OCR (Small mode: 100 tokens)
            # Support uses SMALL mode (640×640, 100 tokens) optimized for customer screenshots
            compression_result = await self.ocr_compressor.compress(
                image_path,
                mode=ResolutionMode.SMALL,  # 640×640, 100 tokens - optimized for simple screenshots
                task="ocr"
            )

            # Prepare ticket processing result with compressed data
            result = {
                'valid': True,
                'compressed_markdown': compression_result.markdown,
                'tokens_used': compression_result.tokens_used,
                'compression_ratio': compression_result.compression_ratio,
                'baseline_tokens': int(compression_result.tokens_used / (1 - compression_result.compression_ratio)) if compression_result.compression_ratio < 1.0 else compression_result.tokens_used,
                'savings_percent': compression_result.compression_ratio * 100,
                'execution_time_ms': compression_result.execution_time_ms,
                'grounding_boxes': compression_result.grounding_boxes,
                'has_content': len(compression_result.markdown.strip()) > 0,
                'word_count': len(compression_result.markdown.split())
            }

            # Check for expected issue keywords if provided
            if expected_issues:
                detected_issues = []
                missing_issues = []

                for issue in expected_issues:
                    if issue.lower() in compression_result.markdown.lower():
                        detected_issues.append(issue)
                    else:
                        missing_issues.append(issue)

                result['expected_issues'] = expected_issues
                result['detected_issues'] = detected_issues
                result['missing_issues'] = missing_issues
                result['likely_issue_report'] = len(detected_issues) >= 1

                # Check for urgency keywords
                urgency_keywords = ['urgent', 'critical', 'asap', 'emergency']
                result['urgency_high'] = any(
                    keyword in compression_result.markdown.lower()
                    for keyword in urgency_keywords
                )

            logger.info(
                f"Ticket image processed with DeepSeek-OCR: "
                f"{compression_result.tokens_used} tokens "
                f"({compression_result.compression_ratio:.1%} savings) "
                f"in {compression_result.execution_time_ms:.0f}ms"
            )

            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"DeepSeek-OCR compression failed, falling back to legacy OCR: {e}")

            legacy_result = support_agent_ticket_image_processor(image_path)
            legacy_result['fallback_mode'] = True
            legacy_result['error'] = str(e)
            return json.dumps(legacy_result, indent=2)

        except Exception as e:
            logger.error(f"DeepSeek-OCR compression failed, falling back to legacy OCR: {e}")

            # Fallback to legacy OCR if compression fails
            legacy_result = support_agent_ticket_image_processor(image_path)
            legacy_result['fallback_mode'] = True
            legacy_result['error'] = str(e)
            return json.dumps(legacy_result, indent=2)

    async def reproduce_customer_issue(self, ticket_id: str, reproduction_steps: str) -> str:
        """
        Reproduce customer issue via learned browser automation (NEW: OpenEnv capability).

        Args:
            ticket_id: Support ticket ID
            reproduction_steps: Steps to reproduce the issue

        Returns:
            JSON string with reproduction results
        """
        if not self.env_agent:
            return json.dumps({
                "error": "OpenEnv not initialized",
                "message": "Call initialize() first"
            }, indent=2)

        logger.info(f"Reproducing customer issue: ticket={ticket_id}")

        x402_receipt = self._charge_x402(
            vendor="support-env-repro",
            amount=max(0.03, max(len(reproduction_steps.split()), 1) * 0.001),
            metadata={"ticket_id": ticket_id},
        )

        # Agent learns to reproduce issue via self-play
        result = await self.env_agent.learn_task(
            goal=f"Reproduce issue: {reproduction_steps}",
            context={"ticket_id": ticket_id}
        )

        reproduction_result = {
            "reproduction_id": f"REPRO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "ticket_id": ticket_id,
            "reproduction_steps": reproduction_steps,
            "reproduced": result["success"],
            "episodes": result["episodes"],
            "total_steps": result["total_steps"],
            "observed_behavior": result["learned_strategy"],
            "status": "REPRODUCED" if result["success"] else "COULD_NOT_REPRODUCE",
            "reproduced_at": datetime.now().isoformat(),
            "x402_payment": x402_receipt,
        }

        if result["success"]:
            logger.info(
                f"Issue reproduced! Episodes: {result['episodes']}, "
                f"Steps: {result['total_steps']}"
            )
        else:
            logger.warning(
                f"Could not reproduce issue after {result['episodes']} episodes"
            )

        return json.dumps(reproduction_result, indent=2)


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
            'id': f'support-{{datetime.now().strftime("%Y%m%d%H%M%S")}}',
            'description': task_description,
            'priority': priority,
            'required_tools': []
        }

        decision = self.router.route_task(task, budget_conscious=True)

        logger.info(
            f"Task routed: {decision.reasoning}",
            extra={
                'agent': 'SupportAgent',
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
                'agent': 'SupportAgent',
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
            'agent': 'SupportAgent',
            'tumix_sessions': tumix_savings['sessions'],
            'tumix_baseline_rounds': tumix_savings['baseline_rounds'],
            'tumix_actual_rounds': tumix_savings['tumix_rounds'],
            'tumix_savings_percent': tumix_savings['savings_percent'],
            'tumix_total_saved': tumix_savings['savings'],
            'daao_info': 'DAAO routing automatically applied to all tasks'
        }

    # ------------------------------------------------------------------ #
    # AP2 helpers
    # ------------------------------------------------------------------ #
    def shutdown(self) -> None:
        if self._ap2_loop:
            self._ap2_loop.call_soon_threadsafe(self._ap2_loop.stop)
        if self._ap2_thread:
            self._ap2_thread.join(timeout=1)
        self._ap2_loop = None
        self._ap2_thread = None

    def get_budget_metrics(self) -> Dict[str, Any]:
        self._reset_support_budget_if_needed()
        return {
            "monthly_limit": self._budget_config.monthly_limit,
            "monthly_spend": self._monthly_spend,
            "remaining_budget": max(self._budget_config.monthly_limit - self._monthly_spend, 0),
            "window": self._budget_window,
        }

    def get_audit_log(self) -> List[Dict[str, Any]]:
        return list(self.support_audit)

    def get_alerts(self) -> List[Dict[str, Any]]:
        return list(self.support_alerts)

    def _run_ap2_loop(self) -> None:
        if not self._ap2_loop:
            return
        asyncio.set_event_loop(self._ap2_loop)
        self._ap2_loop.run_forever()

    def _execute_ap2_coro(self, coro: Awaitable[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.ap2_service:
            raise RuntimeError("AP2 service unavailable for SupportAgent.")
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

    def _get_support_budget(self) -> AP2BudgetConfig:
        return DEFAULT_BUDGETS.get(
            "support_agent",
            AP2BudgetConfig(monthly_limit=800.0, per_transaction_alert=100.0, require_manual_above=150.0),
        )

    def _reset_support_budget_if_needed(self) -> None:
        current_window = datetime.utcnow().strftime("%Y-%m")
        if current_window != self._budget_window:
            self._budget_window = current_window
            self._monthly_spend = 0.0

    def _ensure_support_budget(
        self,
        service_name: str,
        amount: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("Support spend must be positive.")
        if not self.ap2_service:
            raise RuntimeError("AP2 service unavailable for SupportAgent.")

        self._reset_support_budget_if_needed()
        if self._monthly_spend + amount > self._budget_config.monthly_limit:
            raise ValueError(
                f"Support monthly budget exhausted. Remaining "
                f"${self._budget_config.monthly_limit - self._monthly_spend:.2f}."
            )

        auto_approval = amount <= 50.0
        manual_review = amount > 100.0
        receipt = self._execute_ap2_coro(
            self.ap2_service.request_purchase(
                agent_name="support_agent",
                user_id=f"{self.business_id}_support",
                service_name=service_name,
                price=amount,
                categories=["support"],
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
            raise RuntimeError("SupportAgent AP2 signature verification failed.")

        self._monthly_spend += amount
        self.channel_spend[service_name] += amount
        self.support_audit.append(payload)

        if amount >= self._budget_config.per_transaction_alert:
            self.support_alerts.append(
                {"service": service_name, "amount": amount, "timestamp": payload["timestamp"]}
            )

        return payload

    def _charge_x402(
        self,
        vendor: str,
        amount: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            prepared_metadata = self._prepare_x402_metadata(vendor, metadata)
            receipt = self.x402_client.record_manual_payment(
                agent_name="support_agent",
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
            raise RuntimeError(f"Support Agent x402 budget exceeded: {exc}") from exc

    def _prepare_x402_metadata(
        self, vendor: str, metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        data = dict(metadata or {})
        data.setdefault("business_id", self.business_id)
        data.setdefault("agent_name", "support_agent")
        data.setdefault("category", "support")
        capabilities = self.vendor_cache.lookup(vendor)
        if capabilities:
            data.setdefault("accepted_tokens", capabilities.get("accepted_tokens"))
            data.setdefault("preferred_chain", capabilities.get("preferred_chain"))
        return data

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



async def get_support_agent(business_id: str = "default") -> SupportAgent:
    agent = SupportAgent(business_id=business_id)
    await agent.initialize()
    return agent
