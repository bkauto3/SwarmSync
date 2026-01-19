"""
Domain Name Agent - Autonomous Domain Registration and Management
Author: Genesis AI
Date: November 14, 2025
Integration #73: Domain Name Agent

Capabilities:
- Generate business-appropriate domain names (10-20 candidates)
- Check domain availability via Name.com API
- Auto-register available domains with privacy protection
- Configure DNS for GitHub Pages deployment
- Track domain costs and alert if >$100/month
- Manage domain lifecycle (renewals, transfers, deletions)
"""

import os
import logging
import re
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import random
from datetime import datetime
import json

from infrastructure.namecom_client import (
    get_namecom_client,
    NameComClient,
    DomainAvailability,
    DomainRegistration,
    DNSRecord
)
from infrastructure.load_env import load_genesis_env
from infrastructure.ap2_connector import (
    AP2Connector,
    AP2IntentMandate,
    CartItem,
    PaymentMethod,
    PaymentMethodDetails,
    ConsentStatus
)

load_genesis_env()
logger = logging.getLogger(__name__)


@dataclass
class DomainCandidate:
    """Domain name candidate with metadata"""
    domain: str
    score: float  # 0-100, higher is better
    keywords: List[str]
    tld: str
    length: int
    memorable: bool
    brandable: bool


@dataclass
class DomainRegistrationResult:
    """Complete domain registration result"""
    business_name: str
    business_type: str
    selected_domain: str
    candidates_checked: int
    total_cost: float
    registration_success: bool
    dns_configured: bool
    github_pages_ready: bool
    error: Optional[str] = None
    metadata: Optional[Dict] = None
    # AP2 payment tracking
    ap2_intent_mandate_id: Optional[str] = None
    ap2_cart_mandate_id: Optional[str] = None
    ap2_payment_mandate_id: Optional[str] = None
    payment_consent_status: Optional[str] = None


class DomainNameAgent:
    """
    Autonomous Domain Name Agent

    Workflow:
    1. Analyze business name and type
    2. Generate 10-20 domain name candidates
    3. Check availability via Name.com API
    4. Select best available domain
    5. Register domain with privacy
    6. Configure DNS for GitHub Pages
    7. Track costs and alert if needed
    """

    def __init__(
        self,
        namecom_client: Optional[NameComClient] = None,
        cost_alert_threshold: float = 100.0,
        preferred_tlds: Optional[List[str]] = None,
        ap2_connector: Optional[AP2Connector] = None,
        enable_ap2_consent: bool = True
    ):
        """
        Initialize Domain Name Agent

        Args:
            namecom_client: Name.com API client (auto-created if None)
            cost_alert_threshold: Alert if monthly domain costs exceed this amount
            preferred_tlds: Preferred TLDs in order of preference
            ap2_connector: AP2 payment connector (auto-created if None)
            enable_ap2_consent: Require AP2 payment consent for domain purchases
        """
        self.client = namecom_client or get_namecom_client()
        self.cost_alert_threshold = cost_alert_threshold
        self.preferred_tlds = preferred_tlds or [".com", ".ai", ".io", ".app", ".co"]

        # AP2 payment integration
        self.ap2_connector = ap2_connector or AP2Connector()
        self.enable_ap2_consent = enable_ap2_consent
        self.current_intent_mandate: Optional[AP2IntentMandate] = None

        # Cost tracking
        self.total_monthly_cost = 0.0
        self.registered_domains: List[Dict] = []

        logger.info(
            f"DomainNameAgent initialized (threshold=${cost_alert_threshold}, "
            f"preferred_tlds={self.preferred_tlds}, ap2_consent={'enabled' if enable_ap2_consent else 'disabled'})"
        )

    def generate_domain_candidates(
        self,
        business_name: str,
        business_type: str,
        count: int = 20
    ) -> List[DomainCandidate]:
        """
        Generate domain name candidates based on business name and type

        Strategy:
        1. Direct name variations (exact, hyphenated, abbreviated)
        2. Keyword combinations (name + industry keywords)
        3. Brandable alternatives (short, memorable, pronounceable)
        4. TLD variations (try multiple TLDs for each candidate)

        Args:
            business_name: Business name (e.g., "TaskFlow Pro")
            business_type: Business type (e.g., "saas", "ecommerce")
            count: Number of candidates to generate

        Returns:
            List of DomainCandidate objects, sorted by score (best first)
        """
        candidates = []

        # Normalize business name
        clean_name = re.sub(r'[^a-z0-9\s-]', '', business_name.lower())
        words = clean_name.split()

        # Industry keywords by business type
        industry_keywords = {
            "saas": ["app", "cloud", "hub", "pro", "suite", "platform", "software"],
            "ecommerce": ["shop", "store", "market", "buy", "sell", "commerce", "mart"],
            "marketplace": ["market", "exchange", "hub", "connect", "network", "place"],
            "content": ["media", "content", "studio", "post", "blog", "news", "creative"],
            "analytics": ["data", "insights", "metrics", "analytics", "stats", "track"],
            "education": ["learn", "edu", "academy", "school", "course", "teach", "study"],
            "ai": ["ai", "ml", "bot", "neural", "smart", "intelligent", "auto"],
            "fintech": ["pay", "finance", "wallet", "bank", "money", "invest", "cash"],
        }

        keywords = industry_keywords.get(business_type.lower(), ["app", "pro", "hub"])

        # Strategy 1: Direct name variations
        for tld in self.preferred_tlds:
            # Exact match
            domain = "".join(words) + tld
            if 3 <= len("".join(words)) <= 20:
                candidates.append(self._score_domain(domain, words, tld))

            # Hyphenated
            if len(words) > 1:
                domain = "-".join(words) + tld
                if len(domain) <= 30:
                    candidates.append(self._score_domain(domain, words, tld))

            # Abbreviated (first letters of each word)
            if len(words) >= 2:
                abbrev = "".join([w[0] for w in words if w])
                if 2 <= len(abbrev) <= 5:
                    domain = abbrev + tld
                    candidates.append(self._score_domain(domain, words, tld))

        # Strategy 2: Keyword combinations
        for keyword in keywords[:3]:
            for tld in self.preferred_tlds[:3]:
                # name + keyword
                domain = "".join(words[:2]) + keyword + tld
                if len(domain) <= 30:
                    candidates.append(self._score_domain(domain, words + [keyword], tld))

                # keyword + name
                domain = keyword + "".join(words[:2]) + tld
                if len(domain) <= 30:
                    candidates.append(self._score_domain(domain, [keyword] + words, tld))

        # Strategy 3: Brandable alternatives (short + memorable)
        for tld in self.preferred_tlds:
            # Take first 3-6 letters of name
            if len(words) > 0 and len(words[0]) >= 3:
                short = words[0][:random.randint(3, min(6, len(words[0])))]
                domain = short + tld
                candidates.append(self._score_domain(domain, [short], tld))

            # Combine syllables from multiple words
            if len(words) >= 2:
                syllable1 = words[0][:random.randint(2, min(4, len(words[0])))]
                syllable2 = words[1][:random.randint(2, min(4, len(words[1])))]
                domain = syllable1 + syllable2 + tld
                if len(domain) <= 25:
                    candidates.append(self._score_domain(domain, words, tld))

        # Remove duplicates and sort by score
        seen = set()
        unique_candidates = []
        for candidate in candidates:
            if candidate.domain not in seen:
                seen.add(candidate.domain)
                unique_candidates.append(candidate)

        unique_candidates.sort(key=lambda x: x.score, reverse=True)

        return unique_candidates[:count]

    def _score_domain(
        self,
        domain: str,
        keywords: List[str],
        tld: str
    ) -> DomainCandidate:
        """
        Score a domain candidate (0-100)

        Scoring factors:
        - Length: Shorter is better (10-15 chars ideal)
        - TLD: Prefer .com > .ai > .io > .app > .co
        - Memorability: Easy to spell and pronounce
        - Brandability: No hyphens, no numbers preferred
        - Keyword relevance: Contains business keywords

        Args:
            domain: Domain name with TLD
            keywords: Business keywords
            tld: Top-level domain

        Returns:
            DomainCandidate object
        """
        name_part = domain.replace(tld, "")
        length = len(name_part)

        score = 0.0

        # Length scoring (20 points max)
        # Ideal: 6-12 characters
        if 6 <= length <= 12:
            score += 20
        elif 4 <= length <= 15:
            score += 15
        elif 3 <= length <= 20:
            score += 10
        else:
            score += 5

        # TLD scoring (25 points max)
        tld_scores = {".com": 25, ".ai": 22, ".io": 20, ".app": 18, ".co": 15}
        score += tld_scores.get(tld, 10)

        # Brandability scoring (25 points max)
        has_hyphens = "-" in name_part
        has_numbers = any(c.isdigit() for c in name_part)
        is_pronounceable = self._is_pronounceable(name_part)

        if not has_hyphens and not has_numbers and is_pronounceable:
            score += 25  # Perfect brandability
        elif not has_hyphens and is_pronounceable:
            score += 20
        elif is_pronounceable:
            score += 15
        else:
            score += 5

        # Keyword relevance (15 points max)
        keyword_matches = sum(1 for kw in keywords if kw in name_part)
        score += min(15, keyword_matches * 5)

        # Memorability (15 points max)
        # No repeated letters, easy to type
        has_repeated = len(set(name_part)) < len(name_part) * 0.7
        is_memorable = not has_repeated and length <= 12

        if is_memorable:
            score += 15
        elif not has_repeated:
            score += 10
        else:
            score += 5

        return DomainCandidate(
            domain=domain,
            score=min(100.0, score),
            keywords=keywords,
            tld=tld,
            length=length,
            memorable=is_memorable,
            brandable=not has_hyphens and not has_numbers
        )

    def _is_pronounceable(self, name: str) -> bool:
        """
        Check if name is pronounceable (has reasonable vowel/consonant distribution)

        Args:
            name: Domain name without TLD

        Returns:
            True if pronounceable, False otherwise
        """
        vowels = set("aeiou")
        if len(name) < 3:
            return True

        vowel_count = sum(1 for c in name if c in vowels)
        vowel_ratio = vowel_count / len(name)

        # Good pronounceability: 20-60% vowels
        return 0.2 <= vowel_ratio <= 0.6

    async def create_payment_intent_mandate(
        self,
        user_id: str,
        business_name: str,
        business_type: str,
        max_domains: int = 10,
        max_price_per_domain: float = 50.0,
        valid_for_hours: int = 168  # 7 days
    ) -> AP2IntentMandate:
        """
        Create AP2 Intent Mandate for domain purchases

        User authorizes agent to purchase domains within constraints.
        Required before autonomous domain registration.

        Args:
            user_id: User ID authorizing the purchase
            business_name: Business name for intent description
            business_type: Business type (saas, ecommerce, etc.)
            max_domains: Maximum number of domains agent can purchase
            max_price_per_domain: Maximum price per domain (USD)
            valid_for_hours: Intent mandate validity (default: 7 days)

        Returns:
            AP2IntentMandate object
        """
        intent = await self.ap2_connector.create_intent_mandate(
            user_id=user_id,
            agent_id="domain_name_agent",
            task_description=f"Purchase domain names for '{business_name}' ({business_type} business)",
            max_price_cents=int(max_price_per_domain * 100),
            currency="USD",
            valid_for_hours=valid_for_hours,
            allowed_categories=["domains", "dns", "privacy"],
            require_approval=True
        )

        self.current_intent_mandate = intent

        logger.info(
            f"Created AP2 intent mandate {intent.mandate_id} for user {user_id} "
            f"(max ${max_price_per_domain}/domain, up to {max_domains} domains)"
        )

        return intent

    async def _request_payment_consent_ap2(
        self,
        user_id: str,
        domain: str,
        price: float,
        years: int = 1,
        privacy: bool = True
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Request AP2 payment consent for domain registration

        Creates Intent Mandate → Cart Mandate → Request Approval flow.

        Args:
            user_id: User ID
            domain: Domain name to register
            price: Registration price (USD)
            years: Registration period
            privacy: WHOIS privacy protection

        Returns:
            (approved, cart_mandate_id, error_message) tuple
        """
        try:
            # Ensure intent mandate exists
            if not self.current_intent_mandate:
                logger.warning("No intent mandate - creating default mandate")
                self.current_intent_mandate = await self.create_payment_intent_mandate(
                    user_id=user_id,
                    business_name="Unknown",
                    business_type="general"
                )

            # Verify intent mandate is still valid
            if not self.ap2_connector.verify_intent_mandate(self.current_intent_mandate):
                return False, None, "Intent mandate expired or invalid"

            # Create cart item for domain registration
            cart_item = CartItem(
                item_id=f"domain_{domain}",
                name=f"{domain} - {years} year registration {'+ privacy' if privacy else ''}",
                quantity=1,
                unit_price_cents=int(price * 100),
                currency="USD"
            )

            # Create cart mandate
            cart = await self.ap2_connector.create_cart_mandate(
                intent_mandate_id=self.current_intent_mandate.mandate_id,
                items=[cart_item],
                user_id=user_id
            )

            logger.info(
                f"Created cart mandate {cart.mandate_id} for {domain} (${price})"
            )

            # Auto-approve for testing (in production, this would wait for user approval)
            # Check if auto-approval is enabled
            auto_approve = os.getenv("AP2_AUTO_APPROVE_DOMAINS", "false").lower() == "true"

            if auto_approve and price <= 50.0:
                logger.warning(
                    f"AUTO-APPROVING domain purchase: {domain} (${price}) "
                    f"- THIS SHOULD ONLY BE USED FOR TESTING"
                )
                await self.ap2_connector.approve_cart_mandate(cart.mandate_id, user_id)
                return True, cart.mandate_id, None
            else:
                # In production: Return pending status, user must approve via UI
                logger.info(
                    f"Payment consent pending for {domain} - waiting for user approval"
                )
                return False, cart.mandate_id, "Awaiting user approval"

        except Exception as e:
            logger.error(f"AP2 payment consent failed: {e}")
            return False, None, str(e)

    async def select_and_register_domain(
        self,
        business_name: str,
        business_type: str,
        user_id: str = "default_user",
        auto_register: bool = True,
        configure_dns: bool = True,
        max_cost: float = 50.0
    ) -> DomainRegistrationResult:
        """
        Main workflow: Generate, select, and register domain with AP2 payment consent

        Args:
            business_name: Business name
            business_type: Business type (saas, ecommerce, etc.)
            user_id: User ID for AP2 payment consent
            auto_register: Automatically register first available domain
            configure_dns: Configure DNS for GitHub Pages
            max_cost: Maximum cost per domain (USD)

        Returns:
            DomainRegistrationResult object with AP2 mandate tracking
        """
        logger.info(f"Starting domain selection for '{business_name}' ({business_type})")

        # Generate candidates
        candidates = self.generate_domain_candidates(business_name, business_type, count=20)
        logger.info(f"Generated {len(candidates)} domain candidates")

        # Check availability for top candidates
        available_domains = []
        checked_count = 0

        for candidate in candidates:
            checked_count += 1
            availability = self.client.check_availability(candidate.domain)

            if availability.available and availability.purchasable:
                if availability.price <= max_cost:
                    logger.info(
                        f"✅ Available: {candidate.domain} (${availability.price:.2f}, "
                        f"score={candidate.score:.1f})"
                    )
                    available_domains.append((candidate, availability))
                else:
                    logger.warning(
                        f"⚠️  Available but too expensive: {candidate.domain} "
                        f"(${availability.price:.2f} > ${max_cost})"
                    )
            else:
                logger.debug(f"❌ Not available: {candidate.domain}")

            # Stop after finding 3 good options or checking 15 candidates
            if len(available_domains) >= 3 or checked_count >= 15:
                break

        if not available_domains:
            return DomainRegistrationResult(
                business_name=business_name,
                business_type=business_type,
                selected_domain="",
                candidates_checked=checked_count,
                total_cost=0.0,
                registration_success=False,
                dns_configured=False,
                github_pages_ready=False,
                error="No available domains found within budget"
            )

        # Select best available domain (highest score)
        best_candidate, best_availability = available_domains[0]
        selected_domain = best_candidate.domain

        logger.info(
            f"🎯 Selected domain: {selected_domain} (score={best_candidate.score:.1f}, "
            f"price=${best_availability.price:.2f})"
        )

        # Register domain if auto_register=True
        registration_success = False
        dns_configured = False
        total_cost = best_availability.price
        error = None
        ap2_intent_mandate_id = None
        ap2_cart_mandate_id = None
        ap2_payment_mandate_id = None
        payment_consent_status = "not_required"

        if auto_register:
            # Check cost alert threshold
            if self.total_monthly_cost + total_cost > self.cost_alert_threshold:
                error = (
                    f"⚠️  COST ALERT: Total monthly domain cost would be "
                    f"${self.total_monthly_cost + total_cost:.2f}, exceeding threshold "
                    f"${self.cost_alert_threshold:.2f}. Manual approval required."
                )
                logger.error(error)
                return DomainRegistrationResult(
                    business_name=business_name,
                    business_type=business_type,
                    selected_domain=selected_domain,
                    candidates_checked=checked_count,
                    total_cost=total_cost,
                    registration_success=False,
                    dns_configured=False,
                    github_pages_ready=False,
                    error=error,
                    metadata={"best_score": best_candidate.score},
                    payment_consent_status="threshold_exceeded"
                )

            # AP2 Payment Consent (if enabled)
            if self.enable_ap2_consent:
                logger.info(f"Requesting AP2 payment consent for {selected_domain} (${total_cost})")

                # Ensure intent mandate exists
                if not self.current_intent_mandate:
                    self.current_intent_mandate = await self.create_payment_intent_mandate(
                        user_id=user_id,
                        business_name=business_name,
                        business_type=business_type
                    )

                ap2_intent_mandate_id = self.current_intent_mandate.mandate_id

                # Request payment consent via AP2
                consent_approved, cart_mandate_id, consent_error = await self._request_payment_consent_ap2(
                    user_id=user_id,
                    domain=selected_domain,
                    price=total_cost,
                    years=1,
                    privacy=True
                )

                ap2_cart_mandate_id = cart_mandate_id

                if not consent_approved:
                    payment_consent_status = "pending_approval"
                    error = f"AP2 payment consent required: {consent_error or 'Awaiting user approval'}"
                    logger.warning(error)

                    return DomainRegistrationResult(
                        business_name=business_name,
                        business_type=business_type,
                        selected_domain=selected_domain,
                        candidates_checked=checked_count,
                        total_cost=total_cost,
                        registration_success=False,
                        dns_configured=False,
                        github_pages_ready=False,
                        error=error,
                        metadata={"best_score": best_candidate.score},
                        ap2_intent_mandate_id=ap2_intent_mandate_id,
                        ap2_cart_mandate_id=ap2_cart_mandate_id,
                        payment_consent_status=payment_consent_status
                    )

                payment_consent_status = "approved"
                logger.info(f"✅ AP2 payment consent approved for {selected_domain}")

            # Register domain (after AP2 consent if enabled)
            registration = self.client.register_domain(
                domain=selected_domain,
                years=1,
                auto_renew=True,
                privacy=True
            )

            registration_success = registration.success
            total_cost = registration.total_cost

            if registration_success:
                logger.info(
                    f"✅ Domain registered: {selected_domain} "
                    f"(order_id={registration.order_id}, cost=${total_cost:.2f})"
                )

                # Update cost tracking
                self.total_monthly_cost += total_cost / 12  # Amortize annual cost
                self.registered_domains.append({
                    "domain": selected_domain,
                    "business_name": business_name,
                    "registered_at": datetime.now().isoformat(),
                    "cost": total_cost,
                    "ap2_cart_mandate_id": ap2_cart_mandate_id
                })

                # AP2 Audit Logging (if enabled)
                if self.enable_ap2_consent and ap2_cart_mandate_id:
                    try:
                        self.ap2_connector.audit_logger.log_event(
                            event_type="domain_registered",
                            mandate_id=ap2_cart_mandate_id,
                            user_id=user_id,
                            agent_id="domain_name_agent",
                            data={
                                "domain": selected_domain,
                                "business_name": business_name,
                                "business_type": business_type,
                                "order_id": registration.order_id,
                                "cost_usd": total_cost,
                                "years": 1,
                                "privacy": True,
                                "dns_configured": configure_dns
                            }
                        )
                        logger.info(f"📝 AP2 audit log created for {selected_domain}")
                    except Exception as e:
                        logger.warning(f"Failed to create AP2 audit log: {e}")

                # Configure DNS if requested
                if configure_dns:
                    dns_configured = self.client.configure_github_pages(selected_domain)
                    if dns_configured:
                        logger.info(f"✅ DNS configured for GitHub Pages: {selected_domain}")
                    else:
                        logger.error(f"❌ Failed to configure DNS for {selected_domain}")
            else:
                error = f"Registration failed: {registration.error}"
                logger.error(error)

        return DomainRegistrationResult(
            business_name=business_name,
            business_type=business_type,
            selected_domain=selected_domain,
            candidates_checked=checked_count,
            total_cost=total_cost,
            registration_success=registration_success,
            dns_configured=dns_configured,
            github_pages_ready=dns_configured,
            error=error,
            metadata={
                "best_score": best_candidate.score,
                "candidates_found": len(available_domains),
                "total_monthly_cost": self.total_monthly_cost
            },
            ap2_intent_mandate_id=ap2_intent_mandate_id,
            ap2_cart_mandate_id=ap2_cart_mandate_id,
            ap2_payment_mandate_id=ap2_payment_mandate_id,
            payment_consent_status=payment_consent_status
        )

    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get domain cost summary

        Returns:
            Cost summary dict
        """
        return {
            "total_monthly_cost": self.total_monthly_cost,
            "total_domains": len(self.registered_domains),
            "cost_alert_threshold": self.cost_alert_threshold,
            "threshold_exceeded": self.total_monthly_cost > self.cost_alert_threshold,
            "domains": self.registered_domains
        }


def get_domain_agent(
    cost_alert_threshold: Optional[float] = None
) -> DomainNameAgent:
    """
    Factory function to get DomainNameAgent instance

    Args:
        cost_alert_threshold: Override default cost alert threshold

    Returns:
        DomainNameAgent instance
    """
    threshold = cost_alert_threshold or float(
        os.getenv("LARGE_BILL_THRESHOLD", "100.0")
    )
    return DomainNameAgent(cost_alert_threshold=threshold)


if __name__ == "__main__":
    # Test the agent
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test_domain_agent():
        """Test domain agent with AP2 integration"""
        agent = get_domain_agent()

        # Test domain generation and selection (without registration)
        result = await agent.select_and_register_domain(
            business_name="TaskFlow Pro",
            business_type="saas",
            user_id="test_user_123",
            auto_register=False,  # Don't actually register
            configure_dns=False
        )

        print("\n" + "="*80)
        print("DOMAIN NAME AGENT TEST RESULTS (with AP2 Integration)")
        print("="*80)
        print(f"Business: {result.business_name} ({result.business_type})")
        print(f"Selected Domain: {result.selected_domain}")
        print(f"Candidates Checked: {result.candidates_checked}")
        print(f"Estimated Cost: ${result.total_cost:.2f}")
        print(f"Payment Consent: {result.payment_consent_status}")
        if result.ap2_intent_mandate_id:
            print(f"AP2 Intent Mandate: {result.ap2_intent_mandate_id}")
        if result.ap2_cart_mandate_id:
            print(f"AP2 Cart Mandate: {result.ap2_cart_mandate_id}")
        print(f"Metadata: {json.dumps(result.metadata, indent=2)}")
        print("="*80)

        # Print cost summary
        cost_summary = agent.get_cost_summary()
        print("\nCOST SUMMARY:")
        print(json.dumps(cost_summary, indent=2))

    asyncio.run(test_domain_agent())
