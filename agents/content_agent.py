"""
CONTENT AGENT - Microsoft Agent Framework Version
Version: 4.0 (Enhanced with DAAO + TUMIX)

Generates blog posts, documentation, and content marketing materials.
Enhanced with:
- DAAO routing (20-30% cost reduction on varied complexity tasks)
- TUMIX early termination (50-60% cost reduction on iterative content refinement)
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import threading
from datetime import datetime
from typing import List, Dict, Optional, Any, Awaitable
from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from agent_framework.observability import setup_observability
from azure.identity.aio import AzureCliCredential

# Import DAAO and TUMIX
from infrastructure.daao_router import get_daao_router, RoutingDecision
from infrastructure.tumix_termination import (
    get_tumix_termination,
    RefinementResult,
    TerminationDecision
)

# Import MemoryOS MongoDB adapter for persistent memory (NEW: 49% F1 improvement)
from infrastructure.memory_os_mongodb_adapter import (
    GenesisMemoryOSMongoDB,
    create_genesis_memory_mongodb
)
from infrastructure.ap2_service import AP2Service, DEFAULT_BUDGETS, AP2BudgetConfig
from infrastructure.business_monitor import get_monitor
from infrastructure.hallucination_control import BinaryRARVerifier
from infrastructure.x402_client import get_x402_client, X402PaymentError
from infrastructure.creative_asset_registry import get_asset_registry
from infrastructure.x402_vendor_cache import get_x402_vendor_cache

# Import WebVoyager for web navigation and content research (optional - graceful fallback)
try:
    from infrastructure.webvoyager_client import get_webvoyager_client
    WEBVOYAGER_AVAILABLE = True
except ImportError:
    print("[WARNING] WebVoyager not available. Web navigation features will be disabled.")
    WEBVOYAGER_AVAILABLE = False
    get_webvoyager_client = None

setup_observability(enable_sensitive_data=True)
logger = logging.getLogger(__name__)


class ContentAgent:
    """
    Content creation and documentation specialist

    Enhanced with:
    - DAAO: Routes simple content to cheap models, complex long-form to premium
    - TUMIX: Stops iterative refinement when content quality plateaus (saves 50-60%)
    """

    def __init__(self, business_id: str = "default", ap2_service: Optional[AP2Service] = None):
        self.business_id = business_id
        self.agent = None
        self.x402_client = get_x402_client()
        self.vendor_cache = get_x402_vendor_cache()
        self.total_content_spend = 0.0
        self.content_alerts: List[Dict[str, Any]] = []
        self.content_audit: List[Dict[str, Any]] = []
        self._content_monthly_limit = self._get_content_budget_config().monthly_limit
        self._content_monthly_spend = 0.0
        self._content_monthly_window = datetime.utcnow().strftime("%Y-%m")
        self._ap2_secret = os.getenv("AP2_SECRET_KEY", "dev-content-secret")
        self.content_alerts: List[Dict[str, Any]] = []
        self._content_monthly_limit = self._get_content_budget_config().monthly_limit
        self._content_monthly_spend = 0.0
        self._content_monthly_window = datetime.utcnow().strftime("%Y-%m")

        # Initialize DAAO router for cost optimization
        self.router = get_daao_router()

        # Initialize TUMIX for iterative content refinement
        # Content benefits from more refinement: min 2, max 5 rounds
        self.termination = get_tumix_termination(
            min_rounds=2,  # Draft + first revision minimum
            max_rounds=5,  # Content benefits from more refinement
            improvement_threshold=0.05  # 5% improvement threshold (standard)
        )

        # Track refinement sessions for metrics
        self.refinement_history: List[List[RefinementResult]] = []

        # Initialize MemoryOS MongoDB adapter for persistent memory (NEW: 49% F1 improvement)
        # Enables content style memory, topic expertise tracking, brand voice consistency
        self.memory: Optional[GenesisMemoryOSMongoDB] = None
        self._init_memory()

        # Initialize WebVoyager client for web content research (NEW: 59.1% success rate)
        if WEBVOYAGER_AVAILABLE:
            self.webvoyager = get_webvoyager_client(
                headless=True,
                max_iterations=15,
                text_only=False  # Use multimodal (screenshots + GPT-4V)
            )
        else:
            self.webvoyager = None

        logger.info(f"Content Agent v4.0 initialized with DAAO + TUMIX + MemoryOS + WebVoyager for business: {business_id}")
        self.asset_registry = get_asset_registry("content_agent")

        try:
            self.binary_rar = BinaryRARVerifier()
        except Exception as exc:
            logger.warning(f"Binary RAR verifier disabled for ContentAgent: {exc}")
            self.binary_rar = None
        try:
            self.monitor = get_monitor()
        except Exception as exc:
            logger.warning(f"Business monitor unavailable for ContentAgent: {exc}")
            self.monitor = None
        self.ap2_service = ap2_service
        self._ap2_loop: Optional[asyncio.AbstractEventLoop] = None
        self._ap2_thread: Optional[threading.Thread] = None
        if self.ap2_service is None:
            try:
                self.ap2_service = AP2Service()
            except (RuntimeError, OSError) as exc:
                logger.warning("AP2 service unavailable for ContentAgent: %s", exc)
                self.ap2_service = None

        if self.ap2_service:
            self._ap2_loop = asyncio.new_event_loop()
            self._ap2_thread = threading.Thread(
                target=self._run_ap2_loop,
                name="ContentAgent-AP2Loop",
                daemon=True,
            )
            self._ap2_thread.start()

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
                    logger.info("ContentAgent reusing creative asset %s (vendor=%s)", signature, cached.vendor)
                    return {
                        "status": "reused",
                        "signature": signature,
                        "vendor": cached.vendor,
                        "cached_at": cached.timestamp,
                    }
        try:
            prepared_metadata = self._prepare_x402_metadata(vendor, metadata)
            receipt = self.x402_client.record_manual_payment(
                agent_name="content_agent",
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
            raise RuntimeError(f"Content Agent x402 budget exceeded: {exc}") from exc

    def _prepare_x402_metadata(
        self, vendor: str, metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        data = dict(metadata or {})
        data.setdefault("business_id", self.business_id)
        data.setdefault("agent_name", "content_agent")
        data.setdefault("category", "content")
        capabilities = self.vendor_cache.lookup(vendor)
        if capabilities:
            data.setdefault("accepted_tokens", capabilities.get("accepted_tokens"))
            data.setdefault("preferred_chain", capabilities.get("preferred_chain"))
        return data

    def _build_asset_signature(self, vendor: str, metadata: Dict[str, Any]) -> str:
        base = metadata.get("asset_signature")
        if base:
            return str(base)
        title = metadata.get("title") or metadata.get("project") or metadata.get("keywords")
        return f"{vendor}:{title or 'generic'}"

    async def initialize(self):
        cred = AzureCliCredential()
        client = AzureAIAgentClient(async_credential=cred)

        tools = [
            self.write_blog_post,
            self.create_documentation,
            self.generate_faq,
            self.create_video_content,
            self.translate_content,
            self.proofread_content,
            self.subscribe_stock_images,
            self.subscribe_video_platform,
            self.subscribe_translation_api,
            self.subscribe_proofreading_tool,
        ]

        # Add web_content_research tool if WebVoyager is available
        if WEBVOYAGER_AVAILABLE and self.webvoyager:
            tools.append(self.web_content_research)
        tools.append(self.request_content_budget)

        self.agent = ChatAgent(
            chat_client=client,
            instructions="You are an expert content writer specializing in technical documentation and blog posts. Create engaging, SEO-optimized content. For tasks requiring web-based content research (competitor content analysis, trend monitoring, social media research), use the web_content_research tool which employs a multimodal web agent with 59.1% success rate to navigate real websites and extract content.",
            name="content-agent",
            tools=tools
        )
        print(f"📝 Content Agent initialized for business: {self.business_id}")
        print(f"   - MemoryOS MongoDB backend enabled (49% F1 improvement)")
        if WEBVOYAGER_AVAILABLE and self.webvoyager:
            print(f"   - WebVoyager web navigation enabled (59.1% success rate)\n")
        else:
            print(f"   - WebVoyager: NOT AVAILABLE (install dependencies)\n")

    def _init_memory(self):
        """Initialize MemoryOS MongoDB backend for Content creation memory."""
        try:
            import os
            self.memory = create_genesis_memory_mongodb(
                mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017/"),
                database_name="genesis_memory_content",
                short_term_capacity=10,  # Recent content pieces
                mid_term_capacity=600,   # Historical content styles (Content-specific)
                long_term_knowledge_capacity=250  # Brand voice, topic expertise, style preferences
            )
            logger.info("[ContentAgent] MemoryOS MongoDB initialized for content style/topic tracking")
        except Exception as e:
            logger.warning(f"[ContentAgent] Failed to initialize MemoryOS: {e}. Memory features disabled.")
            self.memory = None

    def write_blog_post(
        self,
        title: str,
        keywords: List[str],
        word_count: int = 1000,
        research_tool: str = "BuzzSumo",
        subscription_cost: float = 99.0,
    ) -> str:
        """
        Generate blog post outline with SEO optimization.

        NEW: MemoryOS integration - Retrieves similar content styles and stores brand voice patterns
        for consistency (49% F1 improvement on content quality).
        """
        user_id = f"content_{self.business_id}"

        # Retrieve historical content style patterns from memory
        historical_context = ""
        if self.memory:
            try:
                memories = self.memory.retrieve(
                    agent_id="content",
                    user_id=user_id,
                    query=f"blog post {title} {' '.join(keywords[:3])}",
                    memory_type=None,
                    top_k=3
                )
                if memories:
                    historical_context = "\n".join([
                        f"- Previous content: {m['content'].get('agent_response', '')}"
                        for m in memories
                    ])
                    logger.info(f"[ContentAgent] Retrieved {len(memories)} similar content patterns from memory")
            except Exception as e:
                logger.warning(f"[ContentAgent] Memory retrieval failed: {e}")

        sections = [
            {"heading": "Introduction", "words": int(word_count * 0.15)},
            {"heading": "Main Content Part 1", "words": int(word_count * 0.25)},
            {"heading": "Main Content Part 2", "words": int(word_count * 0.25)},
            {"heading": "Best Practices", "words": int(word_count * 0.20)},
            {"heading": "Conclusion", "words": int(word_count * 0.15)}
        ]

        approval = self._ensure_content_budget(
            service_name=f"{research_tool} subscription",
            amount=subscription_cost,
            metadata={"type": "content_research", "title": title},
        )

        result = {
            "title": title,
            "keywords": keywords,
            "sections": sections,
            "word_count": word_count,
            "historical_context": historical_context if historical_context else "No similar content found",
            "ap2_approval": approval or {"status": "skipped", "reason": "ap2_unavailable"},
        }
        self._charge_x402(
            vendor="content-llm",
            amount=max(0.04, word_count / 20000),
            metadata={"title": title, "keywords": keywords[:5]},
        )

        # Store content creation in memory for future reference
        if self.memory:
            try:
                self.memory.store(
                    agent_id="content",
                    user_id=user_id,
                    user_input=f"Write blog post: {title}",
                    agent_response=f"Created {len(sections)}-section blog post ({word_count} words) with keywords: {', '.join(keywords[:5])}",
                    memory_type="conversation"
                )
                logger.info(f"[ContentAgent] Stored content creation in memory: {title}")
            except Exception as e:
                logger.warning(f"[ContentAgent] Memory storage failed: {e}")

        return json.dumps(result, indent=2)

    def create_documentation(self, product_name: str, sections: List[str]) -> str:
        """Generate technical documentation structure"""
        self._charge_x402(
            vendor="content-docs",
            amount=max(0.03, len(sections) * 0.005),
            metadata={"product": product_name, "sections": sections},
        )
        docs = {section: f"Documentation for {section} in {product_name}" for section in sections}
        return json.dumps({"product": product_name, "docs": docs, "sections": len(sections)})

    def generate_faq(self, product_name: str, num_questions: int = 10) -> str:
        """Generate FAQ questions and answers"""
        self._charge_x402(
            vendor="content-faq",
            amount=max(0.02, num_questions * 0.002),
            metadata={"product": product_name, "questions": num_questions},
        )
        faqs = [{"q": f"Question {i} about {product_name}?", "a": f"Answer {i}"} for i in range(1, num_questions + 1)]
        return json.dumps({"product": product_name, "faqs": faqs, "count": len(faqs)})

    def create_video_content(
        self,
        project_name: str,
        duration_minutes: int = 3,
        hosting_platform: str = "Wistia",
        hosting_cost: float = 49.0,
    ) -> str:
        approval = self._ensure_content_budget(
            service_name=f"{hosting_platform} video hosting",
            amount=hosting_cost,
            metadata={"project": project_name, "duration_minutes": duration_minutes},
        )
        self._charge_x402(
            vendor="content-video",
            amount=max(0.05, duration_minutes * 0.01),
            metadata={
                "project": project_name,
                "platform": hosting_platform,
                "cacheable_asset": True,
                "asset_signature": f"{project_name}:{hosting_platform}:video",
                "asset_ttl_hours": 168,
            },
        )
        storyboard = [
            {"scene": "Hook", "duration": int(duration_minutes * 0.2)},
            {"scene": "Problem", "duration": int(duration_minutes * 0.2)},
            {"scene": "Solution", "duration": int(duration_minutes * 0.3)},
            {"scene": "Demo/Proof", "duration": int(duration_minutes * 0.2)},
            {"scene": "Call to Action", "duration": int(duration_minutes * 0.1)},
        ]
        return json.dumps(
            {
                "project": project_name,
                "duration_minutes": duration_minutes,
                "platform": hosting_platform,
                "storyboard": storyboard,
                "ap2_approval": approval or {"status": "skipped", "reason": "ap2_unavailable"},
            },
            indent=2,
        )

    def translate_content(
        self,
        text: str,
        target_language: str,
        translation_provider: str = "DeepL",
        subscription_cost: float = 25.0,
    ) -> str:
        approval = self._ensure_content_budget(
            service_name=f"{translation_provider} translation",
            amount=subscription_cost,
            metadata={"language": target_language},
        )
        self._charge_x402(
            vendor="content-translation",
            amount=max(0.02, len(text) / 10000),
            metadata={"language": target_language, "provider": translation_provider},
        )
        translated = f"[{target_language}] {text}"
        return json.dumps(
            {
                "original_text": text,
                "translated_text": translated,
                "language": target_language,
                "provider": translation_provider,
                "ap2_approval": approval or {"status": "skipped", "reason": "ap2_unavailable"},
            },
            indent=2,
        )

    def proofread_content(
        self,
        text: str,
        proofreading_tool: str = "Grammarly Business",
        subscription_cost: float = 15.0,
    ) -> str:
        approval = self._ensure_content_budget(
            service_name=f"{proofreading_tool} subscription",
            amount=subscription_cost,
            metadata={"type": "proofreading"},
        )
        self._charge_x402(
            vendor="content-proofreading",
            amount=max(0.015, len(text) / 20000),
            metadata={"tool": proofreading_tool},
        )
        issues = [{"sentence": text[:80], "suggestion": "Improve clarity and conciseness."}]
        return json.dumps(
            {
                "text": text,
                "issues_found": issues,
                "tool": proofreading_tool,
                "ap2_approval": approval or {"status": "skipped", "reason": "ap2_unavailable"},
            },
            indent=2,
        )

    def subscribe_stock_images(
        self,
        provider: str = "Shutterstock",
        monthly_cost: float = 29.0,
    ) -> str:
        approval = self._ensure_content_budget(
            service_name=f"{provider} subscription",
            amount=monthly_cost,
            metadata={"type": "stock_images"},
        )
        return json.dumps(
            {
                "provider": provider,
                "monthly_cost": monthly_cost,
                "ap2_approval": approval or {"status": "skipped", "reason": "ap2_unavailable"},
            },
            indent=2,
        )

    def subscribe_video_platform(
        self,
        platform: str = "Wistia",
        monthly_cost: float = 49.0,
    ) -> str:
        approval = self._ensure_content_budget(
            service_name=f"{platform} subscription",
            amount=monthly_cost,
            metadata={"type": "video_hosting"},
        )
        return json.dumps(
            {
                "platform": platform,
                "monthly_cost": monthly_cost,
                "ap2_approval": approval or {"status": "skipped", "reason": "ap2_unavailable"},
            },
            indent=2,
        )

    def subscribe_translation_api(
        self,
        provider: str = "DeepL",
        monthly_cost: float = 25.0,
    ) -> str:
        approval = self._ensure_content_budget(
            service_name=f"{provider} subscription",
            amount=monthly_cost,
            metadata={"type": "translation_api"},
        )
        return json.dumps(
            {
                "provider": provider,
                "monthly_cost": monthly_cost,
                "ap2_approval": approval or {"status": "skipped", "reason": "ap2_unavailable"},
            },
            indent=2,
        )

    def subscribe_proofreading_tool(
        self,
        provider: str = "Grammarly Business",
        monthly_cost: float = 15.0,
    ) -> str:
        approval = self._ensure_content_budget(
            service_name=f"{provider} subscription",
            amount=monthly_cost,
            metadata={"type": "proofreading"},
        )
        return json.dumps(
            {
                "provider": provider,
                "monthly_cost": monthly_cost,
                "ap2_approval": approval or {"status": "skipped", "reason": "ap2_unavailable"},
            },
            indent=2,
        )

    def generate_campaign_package(
        self,
        project_name: str,
        image_budget: float = 40.0,
        video_budget: float = 80.0,
        translation_budget: float = 35.0,
    ) -> Dict[str, Any]:
        """
        Produce a full content package and collect AP2 receipts for auditing.
        """
        approvals = [
            self._ensure_content_budget(
                service_name="campaign_stock_images",
                amount=image_budget,
                metadata={"project": project_name, "asset": "images"},
            ),
            self._ensure_content_budget(
                service_name="campaign_video_hosting",
                amount=video_budget,
                metadata={"project": project_name, "asset": "video"},
            ),
            self._ensure_content_budget(
                service_name="campaign_translation",
                amount=translation_budget,
                metadata={"project": project_name, "asset": "translation"},
            ),
        ]
        receipts = [approval for approval in approvals if approval]
        return {
            "project_name": project_name,
            "ap2_receipts": receipts,
        }

    def shutdown(self) -> None:
        """Cleanup AP2 background loop."""
        if self._ap2_loop:
            self._ap2_loop.call_soon_threadsafe(self._ap2_loop.stop)
        if self._ap2_thread:
            self._ap2_thread.join(timeout=1)
        self._ap2_loop = None
        self._ap2_thread = None

    def _run_ap2_loop(self) -> None:
        if not self._ap2_loop:
            return
        asyncio.set_event_loop(self._ap2_loop)
        self._ap2_loop.run_forever()

    def _execute_ap2_coro(self, coro: Awaitable[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.ap2_service:
            raise RuntimeError("AP2 service unavailable")
        if self._ap2_loop:
            future = asyncio.run_coroutine_threadsafe(coro, self._ap2_loop)
            try:
                return future.result(timeout=30)
            except asyncio.TimeoutError as exc:
                logger.error("AP2 request timed out: %s", exc, exc_info=True)
                raise RuntimeError("AP2 request timed out") from exc
            except Exception as exc:
                logger.error("AP2 request failed: %s", exc, exc_info=True)
                raise RuntimeError("AP2 request failed") from exc
        try:
            return asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(coro)
        except Exception as exc:
            logger.error("AP2 request failed: %s", exc, exc_info=True)
            raise RuntimeError("AP2 request failed") from exc

    def _get_content_user_id(self) -> str:
        return f"content_{self.business_id or 'default'}"

    def _get_content_budget_config(self) -> AP2BudgetConfig:
        return DEFAULT_BUDGETS.get(
            "content_agent",
            AP2BudgetConfig(monthly_limit=500.0, per_transaction_alert=100.0, require_manual_above=100.0),
        )

    def _validate_content_budget(self, amount: float) -> None:
        config = self._get_content_budget_config()
        if amount <= 0:
            raise ValueError("Content budget requests must be positive.")
        if amount > config.monthly_limit:
            raise ValueError(f"Content budget request ${amount} exceeds monthly limit ${config.monthly_limit}.")

    def _ensure_content_budget(
        self,
        service_name: str,
        amount: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.ap2_service:
            logger.warning("AP2 service unavailable; skipping approval for %s", service_name)
            raise RuntimeError("AP2 service unavailable")
        self._validate_content_budget(amount)
        self._reset_content_budget_if_needed()
        config = self._get_content_budget_config()
        projected_spend = self._content_monthly_spend + amount
        if projected_spend > self._content_monthly_limit:
            raise ValueError(
                f"Content monthly budget exceeded: projected ${projected_spend:.2f} "
                f"(limit ${self._content_monthly_limit:.2f})"
            )
        alert_needed = amount >= config.per_transaction_alert
        manual_review = amount >= config.require_manual_above
        coro = self.request_content_budget(
            user_id=self._get_content_user_id(),
            service_name=service_name,
            amount=amount,
        )
        approval = self._execute_ap2_coro(coro)
        if approval:
            if metadata:
                approval = {**approval, "metadata": metadata}
            payload = {
                **approval,
                "service": service_name,
                "amount": amount,
                "auto_approval": amount <= 50,
                "manual_review": manual_review,
                "timestamp": datetime.utcnow().isoformat(),
            }
            signature = self._sign_content_payload(payload)
            payload["signature"] = signature
            if not self._verify_content_signature(payload, signature):
                raise RuntimeError("AP2 signature verification failed for content agent")
            self.content_audit.append(payload)
            self.total_content_spend += amount
            self._content_monthly_spend = projected_spend
            if alert_needed:
                alert_entry = {
                    "service": service_name,
                    "amount": amount,
                    "timestamp": payload["timestamp"],
                    "metadata": metadata or {},
                }
                self.content_alerts.append(alert_entry)
                logger.warning("Content cost alert triggered for %s: $%s", service_name, amount)
            approval = payload
        return approval

    def _reset_content_budget_if_needed(self) -> None:
        current = datetime.utcnow().strftime("%Y-%m")
        if current != self._content_monthly_window:
            self._content_monthly_window = current
            self._content_monthly_spend = 0.0

    def get_content_budget_metrics(self) -> Dict[str, Any]:
        return {
            "monthly_limit": self._content_monthly_limit,
            "monthly_spend": self._content_monthly_spend,
            "remaining_budget": max(self._content_monthly_limit - self._content_monthly_spend, 0),
            "window": self._content_monthly_window,
        }

    def route_task(self, task_description: str, priority: float = 0.5) -> RoutingDecision:
        """
        Route content task to appropriate model using DAAO

        Args:
            task_description: Description of the content task
            priority: Task priority (0.0-1.0)

        Returns:
            RoutingDecision with model selection and cost estimate
        """
        task = {
            'id': f'content-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'description': task_description,
            'priority': priority,
            'required_tools': []
        }

        decision = self.router.route_task(task, budget_conscious=True)

        logger.info(
            f"Content task routed: {decision.reasoning}",
            extra={
                'agent': 'ContentAgent',
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
                'agent': 'ContentAgent',
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
            'agent': 'ContentAgent',
            'tumix_sessions': tumix_savings['sessions'],
            'tumix_baseline_rounds': tumix_savings['baseline_rounds'],
            'tumix_actual_rounds': tumix_savings['tumix_rounds'],
            'tumix_savings_percent': tumix_savings['savings_percent'],
            'tumix_total_saved': tumix_savings['savings'],
            'daao_info': 'DAAO routing automatically applied to all tasks'
        }

    def get_content_audit(self) -> List[Dict[str, Any]]:
        return list(self.content_audit)

    def _sign_content_payload(self, payload: Dict[str, Any]) -> str:
        body = json.dumps(payload, sort_keys=True)
        return hmac.new(
            self._ap2_secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _verify_content_signature(self, payload: Dict[str, Any], signature: str) -> bool:
        compare_payload = {k: v for k, v in payload.items() if k != "signature"}
        expected = self._sign_content_payload(compare_payload)
        return hmac.compare_digest(signature, expected)

    async def web_content_research(
        self,
        url: str,
        task: str,
        save_screenshots: bool = True
    ) -> str:
        """
        Perform web content research using WebVoyager multimodal agent (NEW: 59.1% success rate).

        This method employs a multimodal web agent for content marketing research tasks like
        competitor content analysis, trend monitoring, social media research, and blog content
        extraction. Ideal for researching content topics, analyzing competitor strategies, and
        extracting inspiration from successful web content.

        Args:
            url: Starting website URL (e.g., "https://www.medium.com")
            task: Natural language task description
                Examples:
                - "Find top 5 AI articles on Medium and extract titles, authors, and engagement metrics"
                - "Navigate to competitor blog and extract latest 3 post titles and topics"
                - "Search Twitter for trending hashtags about AI and summarize top 10 posts"
            save_screenshots: Whether to save trajectory screenshots

        Returns:
            JSON string containing web content research results with metadata

        Example:
            ```python
            result = await content.web_content_research(
                url="https://www.medium.com",
                task="Find trending AI articles and extract titles and topics for blog inspiration"
            )
            ```

        Performance:
        - 59.1% success rate on diverse web tasks (WebVoyager benchmark)
        - Ideal for content research, competitor analysis, trend monitoring
        - 30-50% faster than manual web content research
        """
        import time
        import json
        from datetime import datetime

        if not WEBVOYAGER_AVAILABLE or not self.webvoyager:
            logger.error("WebVoyager not available. Cannot perform web content research.")
            return json.dumps({
                "research_id": f"WEB-ERROR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "url": url,
                "task": task,
                "error": "WebVoyager not available. Install WebVoyager dependencies.",
                "status": "unavailable"
            }, indent=2)

        self._charge_x402(
            vendor="content-web-research",
            amount=0.05,
            metadata={"url": url, "task": task[:120]},
        )
        start_time = time.time()

        logger.info(f"Starting web content research: url='{url}', task='{task}'")

        try:
            # Configure output directory
            output_dir = None
            if save_screenshots:
                output_dir = f"/tmp/webvoyager_content_{self.business_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Execute web navigation task
            result = await self.webvoyager.navigate_and_extract(
                url=url,
                task=task,
                output_dir=output_dir
            )

            elapsed_time = time.time() - start_time

            logger.info(
                f"Web content research {'completed' if result['success'] else 'failed'}: "
                f"iterations={result['iterations']}, "
                f"screenshots={len(result['screenshots'])}, "
                f"time={elapsed_time:.2f}s"
            )

            # Format result for tool output
            result_dict = {
                "research_id": f"WEB-CONTENT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "url": url,
                "task": task,
                "success": result['success'],
                "content_extracted": result['answer'],
                "trajectory": result['trajectory'],
                "metadata": {
                    "iterations": result['iterations'],
                    "screenshots_saved": len(result['screenshots']),
                    "screenshot_dir": output_dir if save_screenshots else None,
                    "elapsed_time_sec": elapsed_time,
                    "timestamp": datetime.now().isoformat(),
                    "final_url": result['trajectory'][-1]['url'] if result['trajectory'] else url,
                    "error": result.get('error')
                }
            }

            rar_report = self._apply_binary_rar_guard(task, result.get("answer", ""))
            if rar_report:
                result_dict["metadata"]["binary_rar"] = rar_report
                result_dict["metadata"]["hallucination_flag"] = rar_report.get("reward") == 0

            # Store web content research in memory for pattern tracking
            if self.memory:
                try:
                    self.memory.store(
                        agent_id="content",
                        user_id=f"content_{self.business_id}",
                        user_message=f"Web content research: {task}",
                        agent_response=result['answer'],
                        context={
                            "url": url,
                            "task": task,
                            "success": result['success'],
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    logger.info("[ContentAgent] Stored web content research in MemoryOS")
                except Exception as e:
                    logger.warning(f"[ContentAgent] Failed to store web content research in memory: {e}")

            return json.dumps(result_dict, indent=2)

        except Exception as e:
            logger.error(f"Web content research failed: {e}", exc_info=True)
            return json.dumps({
                "research_id": f"WEB-CONTENT-ERROR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "url": url,
                "task": task,
                "error": str(e),
                "status": "failed"
            }, indent=2)


    def _apply_binary_rar_guard(self, query: str, response_text: str) -> Optional[Dict[str, Any]]:
        if not self.binary_rar:
            return None
        result = self.binary_rar.verify(query, response_text)
        reward = result.get("reward")
        if self.monitor and reward is not None:
            self.monitor.record_hallucination_event("content_agent", result)
        if reward == 0:
            logger.warning(
                "Binary RAR flagged unsupported content research (task=%s, coverage=%.2f)",
                query,
                result.get("coverage", 0.0),
            )
        return result

    async def request_content_budget(
        self,
        user_id: str,
        service_name: str,
        amount: float
    ) -> Dict[str, Any]:
        """Request AP2 consent for content-related purchases."""
        if not self.ap2_service:
            raise RuntimeError("AP2 service unavailable")

        return await self.ap2_service.request_purchase(
            agent_name="content_agent",
            user_id=user_id,
            service_name=service_name,
            price=amount,
            categories=["content"]
        )


async def get_content_agent(business_id: str = "default") -> ContentAgent:
    agent = ContentAgent(business_id=business_id)
    await agent.initialize()
    return agent
