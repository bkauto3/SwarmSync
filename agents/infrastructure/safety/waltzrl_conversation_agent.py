"""
WaltzRL Conversation Agent - Real LLM + Revision Pipeline
Version: 2.0
Date: October 24, 2025

Provides two capabilities:
1. Async `generate_response` that wraps a backing LLM with safety-aware prompts.
2. Rule-based `improve_response` used by legacy tests to revise unsafe output.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from infrastructure.safety.waltzrl_feedback_agent import (
    FeedbackResult,
    SafetyCategory,
    SafetyIssue,
)

# Import self-correction for safety validation
try:
    from infrastructure.self_correction import (
        SelfCorrectingAgent,
        ValidationCategory,
        get_self_correcting_agent
    )
    SELF_CORRECTION_AVAILABLE = True
except ImportError:
    SELF_CORRECTION_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ConversationResponse:
    """Response from Conversation Agent with safety self-assessment."""

    response: str
    confidence: float
    reasoning: str
    risk_score: float
    risk_categories: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response": self.response,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "risk_score": self.risk_score,
            "risk_categories": self.risk_categories,
            "timestamp": self.timestamp,
        }


@dataclass
class CoachingContext:
    """Context from previous coaching iterations."""

    feedback_history: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)


@dataclass
class SafeResponse:
    """Result produced by improve_response() when revising unsafe output."""

    response: str
    safety_score: float
    helpfulness_score: float
    changes_made: List[str] = field(default_factory=list)
    feedback_incorporated: bool = False
    revision_time_ms: float = 0.0
    original_response: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response": self.response,
            "safety_score": self.safety_score,
            "helpfulness_score": self.helpfulness_score,
            "changes_made": self.changes_made,
            "feedback_incorporated": self.feedback_incorporated,
            "revision_time_ms": self.revision_time_ms,
            "original_response": self.original_response,
            "timestamp": self.timestamp,
        }


class WaltzRLConversationAgent:
    """Conversation agent supporting both real LLM prompting and rule-based fixes."""

    _REFUSAL_PHRASES = (
        "i cannot",
        "i can't",
        "i'm unable",
        "against policy",
    )

    _PII_PATTERNS: Sequence[Tuple[re.Pattern[str], str]] = (
        (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN REDACTED]"),
        (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b"), "[CREDIT CARD REDACTED]"),
        (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[EMAIL REDACTED]"),
        (re.compile(r"(?i)password\s*[:=]\s*[^\s]+"), "password=[REDACTED]"),
    )

    _HELPFUL_RESPONSE_SNIPPET = (
        "Here is a helpful walkthrough:",
        "Let's break this down into steps:",
        "You can approach it this way:",
    )

    _HARMFUL_KEYWORDS = (
        "bomb", "weapon", "attack", "kill", "explosive", "murder",
        "phishing", "hack", "exploit", "malware", "virus",
        "overdose", "suicide", "self-harm", "torture",
        "illegal", "drugs", "cocaine", "heroin", "meth",
        "child abuse", "human trafficking", "terrorism"
    )

    def __init__(
        self,
        llm_client: Any = None,
        memory_store: Optional[Any] = None,
        enable_memory: bool = False,
        max_revision_attempts: int = 3,
        min_safety_improvement: float = 0.1,
        preserve_helpfulness: bool = True,
        enable_safety_filter: bool = False,
        enable_llm_rewriting: bool = True,
    ):
        self.llm_client = llm_client
        self.memory_store = memory_store
        self.enable_memory = enable_memory
        self.max_revision_attempts = max_revision_attempts
        self.min_safety_improvement = min_safety_improvement
        self.preserve_helpfulness = preserve_helpfulness
        self.enable_safety_filter = enable_safety_filter
        self.enable_llm_rewriting = enable_llm_rewriting

        # Self-correction integration (optional)
        self.self_correcting: Optional[Any] = None

        logger.info(
            "WaltzRLConversationAgent initialized (memory=%s, max_attempts=%s, safety_filter=%s, llm_rewriting=%s)",
            enable_memory,
            max_revision_attempts,
            enable_safety_filter,
            enable_llm_rewriting,
        )

    async def enable_self_correction(self, qa_agent: Any, max_attempts: int = 3):
        """
        Enable self-correction QA loop for safety validation.

        Args:
            qa_agent: QA agent for validation (can use feedback agent)
            max_attempts: Maximum correction attempts
        """
        if not SELF_CORRECTION_AVAILABLE:
            logger.warning("Self-correction not available (import failed)")
            return

        self.self_correcting = get_self_correcting_agent(
            agent=self,
            qa_agent=qa_agent,
            max_attempts=max_attempts,
            validation_categories=[
                ValidationCategory.SAFETY,
                ValidationCategory.CORRECTNESS,
                ValidationCategory.QUALITY
            ]
        )
        logger.info(
            f"WaltzRL self-correction enabled: max_attempts={max_attempts}"
        )

    async def _call_llm(self, prompt: str) -> str:
        if self.llm_client is None:
            await asyncio.sleep(0)
            return json.dumps(
                {
                    "response": "I would provide a helpful answer here.",
                    "confidence": 0.5,
                    "reasoning": "Mock response - replace with real LLM.",
                    "risk_score": 0.3,
                    "risk_categories": ["mock"],
                }
            )

        try:
            if hasattr(self.llm_client, "generate"):
                return await self.llm_client.generate(prompt, max_tokens=1024, temperature=0.7)
            if hasattr(self.llm_client, "complete"):
                return await asyncio.to_thread(self.llm_client.complete, prompt=prompt)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("LLM call failed: %s", exc)
        await asyncio.sleep(0)
        return json.dumps(
            {
                "response": "I'm sorry, I can't help with that right now.",
                "confidence": 0.4,
                "reasoning": "LLM unavailable",
                "risk_score": 0.5,
                "risk_categories": ["llm_fallback"],
            }
        )

    async def generate_response(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]] = None,
        coaching_context: Optional[CoachingContext] = None,
        correlation_id: Optional[str] = None,
    ) -> ConversationResponse:
        prompt = self._build_prompt(user_request, context, coaching_context)
        llm_response = await self._call_llm(prompt)
        conversation_response = self._parse_response(llm_response, user_request)

        logger.info(
            "Generated response (risk=%.2f, confidence=%.2f)",
            conversation_response.risk_score,
            conversation_response.confidence,
            extra={"correlation_id": correlation_id} if correlation_id else {},
        )

        return conversation_response

    def _build_prompt(
        self,
        user_request: str,
        context: Optional[Dict[str, Any]],
        coaching_context: Optional[CoachingContext],
    ) -> str:
        prompt = """You are a helpful but safety-aware assistant. Follow these guidelines:
1. Refuse clearly harmful or illegal requests.
2. Be helpful for legitimate questions.
3. Ask for clarification if intent is ambiguous.
4. Provide alternatives when refusing.

Return ONLY valid JSON with keys: response, confidence, reasoning, risk_score, risk_categories (list).

USER_REQUEST:
{user_request}
""".format(user_request=user_request)

        if coaching_context and coaching_context.improvement_suggestions:
            prompt += "\nCOACHING_HINTS:\n"
            for hint in coaching_context.improvement_suggestions[:3]:
                prompt += f"- {hint}\n"

        return prompt

    def _parse_response(self, llm_response: str, user_request: str) -> ConversationResponse:
        try:
            json_text = self._extract_json_from_markdown(llm_response)
            data = json.loads(json_text)
            if not self._validate_response_json(data):
                raise ValueError("Missing required fields")
            return ConversationResponse(
                response=data.get("response", llm_response),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", "No reasoning provided"),
                risk_score=float(data.get("risk_score", 0.5)),
                risk_categories=list(data.get("risk_categories", [])),
            )
        except Exception as exc:  # pragma: no cover - fallback path
            logger.debug("Falling back to heuristic parse: %s", exc)
            return self._fallback_parse(llm_response, user_request)

    def _extract_json_from_markdown(self, text: str) -> str:
        pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            return brace_match.group(0)
        return text

    def _validate_response_json(self, data: Dict[str, Any]) -> bool:
        return "response" in data

    def _fallback_parse(self, llm_response: str, user_request: str) -> ConversationResponse:
        risk_score = self._estimate_risk_from_text(llm_response, user_request)
        reasoning = "Fallback parsing - no structured output"
        risk_categories: List[str] = []
        if risk_score >= 0.7:
            risk_categories.append("high_risk")
        elif risk_score >= 0.4:
            risk_categories.append("ambiguous")
        return ConversationResponse(
            response=llm_response,
            confidence=0.5,
            reasoning=reasoning,
            risk_score=risk_score,
            risk_categories=risk_categories,
        )

    def _estimate_risk_from_text(self, response: str, request: str) -> float:
        harmful_keywords = [
            "bomb",
            "weapon",
            "attack",
            "kill",
            "explosive",
            "phishing",
            "hack",
            "overdose",
        ]
        request_lower = request.lower()
        response_lower = response.lower()
        if any(keyword in request_lower for keyword in harmful_keywords):
            return 0.8
        if any(phrase in response_lower for phrase in self._REFUSAL_PHRASES):
            return 0.7
        return 0.3

    def improve_response(
        self,
        original_response: str,
        feedback: FeedbackResult,
        query: Optional[str] = None,
        agent_type: str = "unknown",
    ) -> SafeResponse:
        start_time = time.time()

        if not feedback.issues_found:
            logger.debug("No issues found; returning original response")
            return SafeResponse(
                response=original_response,
                safety_score=feedback.safety_score,
                helpfulness_score=feedback.helpfulness_score,
                changes_made=[],
                feedback_incorporated=False,
                revision_time_ms=(time.time() - start_time) * 1000,
                original_response=original_response,
            )

        improved_response = original_response
        current_safety = feedback.safety_score
        current_helpfulness = feedback.helpfulness_score
        changes: List[str] = []

        for attempt in range(self.max_revision_attempts):
            revised_response, applied_changes = self._apply_feedback(
                improved_response,
                feedback,
                query=query,
            )

            if not applied_changes:
                break

            is_better, new_safety, new_helpfulness = self._validate_improvement(
                original_response=original_response,
                revised_response=revised_response,
                current_safety_score=current_safety,
                current_helpfulness_score=current_helpfulness,
                feedback=feedback,
            )

            if not is_better:
                logger.debug("Revision attempt %s did not improve response", attempt + 1)
                break

            improved_response = revised_response
            changes.extend(applied_changes)
            current_safety = new_safety
            current_helpfulness = new_helpfulness

        revision_time_ms = (time.time() - start_time) * 1000

        return SafeResponse(
            response=improved_response,
            safety_score=min(1.0, current_safety),
            helpfulness_score=max(0.0, min(1.0, current_helpfulness)),
            changes_made=changes,
            feedback_incorporated=bool(changes),
            revision_time_ms=revision_time_ms,
            original_response=original_response,
        )

    def _apply_feedback(
        self,
        response: str,
        feedback: FeedbackResult,
        query: Optional[str] = None,
    ) -> Tuple[str, List[str]]:
        revised = response
        changes: List[str] = []

        for issue in feedback.issues_found:
            if issue.category == SafetyCategory.HARMFUL_CONTENT:
                revised, change = self._revise_for_safety(revised, issue)
                if change:
                    changes.append(f"Removed harmful content: {issue.description}")

            elif issue.category == SafetyCategory.PRIVACY_VIOLATION:
                revised, change = self._redact_sensitive_data(revised, issue)
                if change:
                    changes.append(f"Redacted sensitive data: {issue.description}")

            elif issue.category == SafetyCategory.MALICIOUS_INSTRUCTION:
                revised, change = self._revise_for_safety(revised, issue)
                if change:
                    changes.append(f"Removed malicious instruction: {issue.description}")

            elif issue.category == SafetyCategory.OVER_REFUSAL:
                revised, change = self._revise_for_helpfulness(revised, issue, query)
                if change:
                    changes.append(f"Improved helpfulness: {issue.description}")

            elif issue.category == SafetyCategory.CAPABILITY_DEGRADED:
                revised, change = self._enhance_response_quality(revised, issue)
                if change:
                    changes.append(f"Enhanced quality: {issue.description}")

        return revised, changes

    def _revise_for_safety(self, response: str, issue: SafetyIssue) -> Tuple[str, bool]:
        if issue.evidence:
            escaped = re.escape(issue.evidence)
            revised = re.sub(escaped, "[CONTENT REMOVED - SAFETY]", response, flags=re.IGNORECASE)
            if revised != response:
                return revised, True

        safe_decline = (
            "I cannot provide that information because it could be harmful or unsafe. "
            "I'm happy to help with constructive or educational requests instead."
        )
        return safe_decline, True

    def _redact_sensitive_data(self, response: str, issue: SafetyIssue) -> Tuple[str, bool]:
        revised = response
        for pattern, replacement in self._PII_PATTERNS:
            if pattern.search(revised):
                revised = pattern.sub(replacement, revised)
        return (revised, revised != response)

    def _contains_harmful_keywords(self, text: str) -> bool:
        """
        Check if text contains harmful keywords (safety filter).

        Args:
            text: Text to check

        Returns:
            True if harmful keywords detected, False otherwise
        """
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self._HARMFUL_KEYWORDS)

    async def _llm_rewrite_refusal(
        self,
        refusal_response: str,
        user_query: str,
    ) -> str:
        """
        Use LLM to intelligently rewrite refusal to be more helpful.

        Args:
            refusal_response: Original refusal response
            user_query: User's original query

        Returns:
            Rewritten helpful response
        """
        system_prompt = """You are a helpful assistant that rewrites refusals to be more constructive and helpful while maintaining safety boundaries.

When given a refusal response, rewrite it to:
1. Acknowledge what the user is asking about
2. Explain why direct help isn't possible (if applicable)
3. Offer alternative approaches or related help
4. Be specific and actionable

DO NOT:
- Provide harmful, illegal, or unethical information
- Be overly apologetic or verbose
- Just say "I can help" without specifics

Keep the response concise (2-4 sentences) and genuinely helpful."""

        user_prompt = f"""Original refusal: "{refusal_response}"
User query: "{user_query}"

Rewrite this refusal to be more helpful while maintaining safety. Provide ONLY the rewritten response, no explanations."""

        try:
            if self.llm_client and hasattr(self.llm_client, 'generate_text'):
                # Use LLM client's generate_text method (Sonnet 4.5 for nuance)
                rewritten = await self.llm_client.generate_text(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.7,
                    max_tokens=256
                )
                return rewritten.strip()
            else:
                # Fallback to _call_llm if no generate_text method
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                llm_response = await self._call_llm(full_prompt)

                # Parse JSON response if it's in that format
                try:
                    data = json.loads(llm_response)
                    if "response" in data:
                        return data["response"]
                except (json.JSONDecodeError, KeyError):
                    pass

                # Return raw response
                return llm_response.strip()

        except Exception as exc:
            logger.warning(f"LLM rewriting failed: {exc}, using fallback template")
            # Fallback to template-based rewriting
            return self._fallback_rewrite_refusal(refusal_response, user_query)

    def _fallback_rewrite_refusal(
        self,
        refusal_response: str,
        user_query: Optional[str],
    ) -> str:
        """
        Fallback template-based refusal rewriting (when LLM unavailable).

        Args:
            refusal_response: Original refusal
            user_query: User's query

        Returns:
            Template-based helpful response
        """
        if user_query:
            helpful_intro = f"I understand you're asking about {user_query}."
        else:
            helpful_intro = "I understand your request."

        helpful_body = (
            "While I can't directly provide what you asked for, I can help you with:\n"
            "1. Understanding the underlying concepts\n"
            "2. Exploring alternative approaches\n"
            "3. Providing relevant resources or references\n\n"
            "Could you clarify what specific aspect you'd like help with?"
        )

        return f"{helpful_intro}\n\n{helpful_body}"

    def _revise_for_helpfulness(
        self,
        response: str,
        issue: SafetyIssue,
        query: Optional[str],
    ) -> Tuple[str, bool]:
        """
        Revise refusal responses to be more helpful (WaltzRL over-refusal reduction).

        This method implements intelligent refusal rewriting:
        1. Safety filter: Block obviously harmful requests
        2. LLM rewriting: Use Claude Sonnet to rewrite refusals helpfully
        3. Fallback: Template-based rewriting if LLM unavailable

        Args:
            response: Current response
            issue: Safety issue detected
            query: User's original query

        Returns:
            Tuple of (revised_response, was_changed)
        """
        lowered = response.lower()
        if not any(phrase in lowered for phrase in self._REFUSAL_PHRASES):
            return response, False

        # Safety filter: Block obviously harmful requests
        if self.enable_safety_filter and query and self._contains_harmful_keywords(query):
            logger.warning(f"Safety filter blocked harmful query: {query[:50]}...")
            return "I'm unable to assist with that request.", True

        # LLM-based refusal rewriting (async, but called from sync context)
        if self.enable_llm_rewriting:
            try:
                # Try to run async rewriting in event loop
                import asyncio
                try:
                    # Try to get existing event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, create a task
                        # Note: This won't work in sync context, fallback to template
                        logger.debug("Event loop running, using fallback template")
                        new_response = self._fallback_rewrite_refusal(response, query)
                    else:
                        # Run in existing loop
                        new_response = loop.run_until_complete(
                            self._llm_rewrite_refusal(response, query or "")
                        )
                except RuntimeError:
                    # No event loop, create new one
                    new_response = asyncio.run(
                        self._llm_rewrite_refusal(response, query or "")
                    )

                return new_response, True

            except Exception as exc:
                logger.warning(f"LLM rewriting failed: {exc}, using fallback")
                new_response = self._fallback_rewrite_refusal(response, query)
                return new_response, True
        else:
            # LLM rewriting disabled, use fallback template
            new_response = self._fallback_rewrite_refusal(response, query)
            return new_response, True

    def _enhance_response_quality(self, response: str, issue: SafetyIssue) -> Tuple[str, bool]:
        if len(response.strip()) > 40:
            return response, False

        enhancement = (
            "Here's a more detailed explanation: provide context, break the solution into clear steps, "
            "and highlight potential pitfalls or best practices so the reader can act confidently."
        )
        new_response = f"{response.strip()}\n\n{enhancement}" if response.strip() else enhancement
        return new_response, True

    def _validate_improvement(
        self,
        original_response: str,
        revised_response: str,
        current_safety_score: float,
        current_helpfulness_score: float,
        feedback: FeedbackResult,
    ) -> Tuple[bool, float, float]:
        if revised_response == original_response:
            return False, current_safety_score, current_helpfulness_score

        new_safety = current_safety_score
        new_helpfulness = current_helpfulness_score
        over_refusal_flag = any(
            issue.category == SafetyCategory.OVER_REFUSAL for issue in feedback.issues_found
        )

        # Safety filter blocking (always an improvement)
        if "unable to assist with that request" in revised_response.lower():
            new_safety = 1.0  # Maximum safety for blocked harmful requests
            return True, new_safety, new_helpfulness

        if "[CONTENT REMOVED - SAFETY]" in revised_response or "I cannot provide" in revised_response:
            new_safety = max(current_safety_score, min(1.0, current_safety_score + 0.2))

        if "[SSN REDACTED]" in revised_response or "[CREDIT CARD REDACTED]" in revised_response:
            new_safety = max(new_safety, 0.9)

        # Helpfulness improvement detection (for refusal rewriting)
        if any(phrase in revised_response.lower() for phrase in ("here's", "let's", "step", "understand", "can help", "i'd be happy")):
            new_helpfulness = max(current_helpfulness_score, min(1.0, current_helpfulness_score + 0.2))
        elif over_refusal_flag and revised_response != original_response:
            # Treat revised refusals with new content as helpful even without keyword heuristics.
            new_helpfulness = max(current_helpfulness_score, min(1.0, current_helpfulness_score + 0.2))

        improved_safety = new_safety >= current_safety_score + self.min_safety_improvement
        if self.preserve_helpfulness:
            improved_helpfulness = new_helpfulness > current_helpfulness_score
        else:
            improved_helpfulness = True

        if over_refusal_flag and revised_response != original_response:
            improved_helpfulness = True

        return (improved_safety or improved_helpfulness), new_safety, new_helpfulness

def get_waltzrl_conversation_agent(
    llm_client: Any = None,
    memory_store: Optional[Any] = None,
    enable_memory: bool = False,
    max_revision_attempts: int = 3,
    min_safety_improvement: float = 0.1,
    preserve_helpfulness: bool = True,
    enable_safety_filter: bool = False,
    enable_llm_rewriting: bool = True,
) -> WaltzRLConversationAgent:
    return WaltzRLConversationAgent(
        llm_client=llm_client,
        memory_store=memory_store,
        enable_memory=enable_memory,
        max_revision_attempts=max_revision_attempts,
        min_safety_improvement=min_safety_improvement,
        preserve_helpfulness=preserve_helpfulness,
        enable_safety_filter=enable_safety_filter,
        enable_llm_rewriting=enable_llm_rewriting,
    )


__all__ = [
    "CoachingContext",
    "ConversationResponse",
    "SafeResponse",
    "WaltzRLConversationAgent",
    "get_waltzrl_conversation_agent",
]
