"""
Intelligent Business Idea Generator

Autonomously generates creative, profitable business ideas using:
- Market trend analysis
- LLM creativity (GPT-4o/Claude)
- Revenue potential scoring
- Memory-backed learning from past successes

This enables Genesis to create 100s of businesses without human input.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import random

logger = logging.getLogger(__name__)


@dataclass
class BusinessIdea:
    """A generated business idea with all requirements."""
    name: str
    business_type: str  # ecommerce, saas, content
    description: str
    target_audience: str
    monetization_model: str
    mvp_features: List[str]
    tech_stack: List[str]
    success_metrics: Dict[str, str]
    revenue_score: float  # 0-100, estimated revenue potential
    market_trend_score: float  # 0-100, alignment with trends
    differentiation_score: float  # 0-100, uniqueness
    overall_score: float  # Weighted average
    generated_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketTrendAnalyzer:
    """
    Analyzes market trends to guide business idea generation.
    
    Uses:
    - Product Hunt trending products
    - Google Trends data
    - HackerNews popular posts
    - Reddit trending topics
    - Twitter/X trending hashtags
    """
    
    async def get_trending_categories(self) -> List[str]:
        """Get trending business categories."""
        # For now, return curated list based on 2025 trends
        # In production, this would scrape real-time data
        trends = [
            "AI productivity tools",
            "Creator economy platforms",
            "Sustainable e-commerce",
            "Remote work SaaS",
            "Health & wellness apps",
            "Educational technology",
            "No-code/low-code platforms",
            "Web3/blockchain tools",
            "Climate tech solutions",
            "Mental health apps",
            "Subscription box services",
            "Micro-SaaS tools",
            "Community platforms",
            "Automation tools",
            "Personal finance apps"
        ]
        
        # Return 5 random trending categories
        return random.sample(trends, min(5, len(trends)))
    
    async def get_market_gaps(self, category: str) -> List[str]:
        """Identify gaps in the market for a category."""
        # Simulated market gap analysis
        # In production, this would use web scraping + LLM analysis
        
        gaps_by_category = {
            "AI productivity tools": [
                "AI-powered meeting note taker with action items",
                "Browser extension for AI email drafting",
                "AI document summarizer for legal/medical",
                "AI-powered code review assistant"
            ],
            "Creator economy platforms": [
                "Sponsorship marketplace for micro-influencers",
                "Analytics dashboard for multi-platform creators",
                "Digital product delivery platform",
                "Creator collaboration matching"
            ],
            "Sustainable e-commerce": [
                "Carbon-offset calculator for purchases",
                "Secondhand marketplace for specific niches",
                "Sustainable product comparison tool",
                "Eco-friendly packaging marketplace"
            ],
            # Add more as needed
        }
        
        return gaps_by_category.get(category, [
            f"Innovative {category} solution",
            f"B2B {category} platform",
            f"{category} marketplace"
        ])
    
    async def analyze_competition(self, idea_description: str) -> Dict[str, Any]:
        """Analyze competition for a business idea."""
        # Simulated competition analysis
        # In production, this would search Product Hunt, Google, etc.
        
        return {
            "competition_level": random.choice(["low", "medium", "high"]),
            "market_saturation": random.uniform(0.2, 0.8),
            "differentiation_opportunity": random.uniform(0.3, 0.9),
            "estimated_competitors": random.randint(5, 50)
        }


class RevenuePotentialScorer:
    """
    Scores business ideas based on revenue potential.
    
    Factors:
    - Market size (TAM)
    - Monetization model viability
    - Customer acquisition cost
    - Pricing potential
    - Scalability
    """
    
    def score_idea(self, idea: Dict[str, Any], market_data: Dict[str, Any]) -> float:
        """
        Score an idea's revenue potential (0-100).
        
        Args:
            idea: Business idea dict
            market_data: Market analysis data
        
        Returns:
            Score from 0-100 (higher = more profitable)
        """
        scores = []
        
        # 1. Market size score
        market_size_score = self._score_market_size(idea["business_type"])
        scores.append(market_size_score * 0.3)  # 30% weight
        
        # 2. Monetization model score
        monetization_score = self._score_monetization(idea.get("monetization_model", ""))
        scores.append(monetization_score * 0.25)  # 25% weight
        
        # 3. Competition score (inverse - less competition = higher score)
        competition_level = market_data.get("competition_level", "medium")
        competition_score = {"low": 90, "medium": 60, "high": 30}.get(competition_level, 50)
        scores.append(competition_score * 0.2)  # 20% weight
        
        # 4. Feature viability score
        feature_score = self._score_features(idea.get("mvp_features", []))
        scores.append(feature_score * 0.15)  # 15% weight
        
        # 5. Tech stack score (how easy to build)
        tech_score = self._score_tech_stack(idea.get("tech_stack", []))
        scores.append(tech_score * 0.10)  # 10% weight
        
        overall_score = sum(scores)
        logger.debug(f"Scored '{idea.get('name', 'unknown')}': {overall_score:.1f}/100")
        
        return overall_score
    
    def _score_market_size(self, business_type: str) -> float:
        """Score based on market size."""
        market_sizes = {
            "saas": 85,  # Large B2B SaaS market
            "ecommerce": 75,  # Mature but huge market
            "content": 60,  # Competitive content market
            "marketplace": 80,  # High-value two-sided markets
            "subscription": 85,  # Recurring revenue
        }
        return market_sizes.get(business_type, 65)
    
    def _score_monetization(self, model: str) -> float:
        """Score monetization model viability."""
        if not model:
            return 50
        
        model_lower = model.lower()
        
        if "subscription" in model_lower or "recurring" in model_lower:
            return 95  # Best: recurring revenue
        elif "saas" in model_lower or "monthly" in model_lower:
            return 90
        elif "marketplace" in model_lower or "commission" in model_lower:
            return 85  # Good: transaction-based
        elif "one-time" in model_lower or "purchase" in model_lower:
            return 70
        elif "ads" in model_lower or "advertising" in model_lower:
            return 60  # Harder: need scale
        elif "freemium" in model_lower:
            return 75
        else:
            return 65
    
    def _score_features(self, features: List[str]) -> float:
        """Score based on feature complexity and value."""
        if not features:
            return 50
        
        # More features = more value (up to a point)
        feature_count_score = min(len(features) * 15, 80)
        
        # Bonus for high-value features
        high_value_keywords = ["ai", "automation", "analytics", "payment", "api", "integration"]
        value_bonus = sum(5 for f in features if any(kw in f.lower() for kw in high_value_keywords))
        
        return min(feature_count_score + value_bonus, 100)
    
    def _score_tech_stack(self, tech_stack: List[str]) -> float:
        """Score based on how easy/fast to build."""
        if not tech_stack:
            return 50
        
        # Prefer modern, agent-friendly stacks
        preferred_tech = {
            "next.js": 95,
            "react": 90,
            "typescript": 95,
            "tailwind": 90,
            "vercel": 95,
            "stripe": 85,
            "supabase": 85,
            "postgresql": 80
        }
        
        scores = [preferred_tech.get(tech.lower(), 60) for tech in tech_stack]
        return sum(scores) / len(scores) if scores else 60


class BusinessIdeaGenerator:
    """
    Generates creative, profitable business ideas autonomously.
    
    Uses:
    - Market trend analysis
    - LLM creativity (GPT-4o or Claude)
    - Revenue potential scoring
    - Memory of past successful businesses
    """
    
    def __init__(self):
        """Initialize idea generator."""
        self.trend_analyzer = MarketTrendAnalyzer()
        self.revenue_scorer = RevenuePotentialScorer()
        
        # LLM for creative idea generation
        self.use_openai = os.getenv('OPENAI_API_KEY', '') != ''
        self.use_anthropic = os.getenv('ANTHROPIC_API_KEY', '') != ''
        
        logger.info(f"BusinessIdeaGenerator initialized (OpenAI={self.use_openai}, Anthropic={self.use_anthropic})")
    
    async def generate_idea(
        self,
        business_type: Optional[str] = None,
        min_revenue_score: float = 70.0,
        max_attempts: int = 5
    ) -> BusinessIdea:
        """
        Generate a single high-quality business idea.
        
        Args:
            business_type: Optional type constraint (ecommerce, saas, content)
            min_revenue_score: Minimum revenue potential score (0-100)
            max_attempts: Maximum attempts to find good idea
        
        Returns:
            BusinessIdea with high revenue potential
        """
        logger.info(f"Generating business idea (type={business_type or 'any'}, min_score={min_revenue_score})")

        # Initialize to track last attempt
        last_idea = None

        for attempt in range(max_attempts):
            # Step 1: Get market trends
            trends = await self.trend_analyzer.get_trending_categories()

            # Step 2: Pick a type (random if not specified)
            if business_type is None:
                business_type = random.choice(["ecommerce", "saas", "content"])

            # Step 3: Generate creative idea using LLM
            idea_data = await self._generate_creative_idea(business_type, trends)

            # Step 4: Analyze market competition
            market_data = await self.trend_analyzer.analyze_competition(idea_data["description"])

            # Step 5: Score revenue potential
            revenue_score = self.revenue_scorer.score_idea(idea_data, market_data)

            # Step 6: Score market trends
            trend_score = self._score_trend_alignment(idea_data, trends)

            # Step 7: Score differentiation
            diff_score = self._score_differentiation(idea_data, market_data)

            # Step 8: Calculate overall score
            overall_score = (revenue_score * 0.5) + (trend_score * 0.3) + (diff_score * 0.2)

            logger.info(f"Attempt {attempt + 1}: '{idea_data['name']}' scored {overall_score:.1f}/100")

            # Create idea object (store as last_idea for fallback)
            idea = BusinessIdea(
                **idea_data,
                revenue_score=revenue_score,
                market_trend_score=trend_score,
                differentiation_score=diff_score,
                overall_score=overall_score,
                generated_at=datetime.utcnow().isoformat()
            )
            last_idea = idea

            if overall_score >= min_revenue_score:
                # Found a good idea!
                logger.info(f"✅ Generated high-quality idea: '{idea.name}' (score={overall_score:.1f})")
                return idea

        # All attempts exhausted - return last attempt
        logger.warning(f"No ideas scored above {min_revenue_score} in {max_attempts} attempts, returning last")
        return last_idea  # Return last idea even if below threshold
    
    async def generate_batch(
        self,
        count: int,
        business_types: Optional[List[str]] = None,
        min_revenue_score: float = 70.0
    ) -> List[BusinessIdea]:
        """
        Generate multiple business ideas in parallel.
        
        Args:
            count: Number of ideas to generate
            business_types: Optional list of types to generate
            min_revenue_score: Minimum score threshold
        
        Returns:
            List of BusinessIdea objects
        """
        logger.info(f"Generating batch of {count} business ideas...")
        
        if business_types is None:
            # Mix of types
            types = ["ecommerce", "saas", "content"] * (count // 3 + 1)
            business_types = types[:count]
        
        # Generate in parallel
        tasks = [
            self.generate_idea(business_type=bt, min_revenue_score=min_revenue_score)
            for bt in business_types
        ]
        
        ideas = await asyncio.gather(*tasks)
        
        # Sort by score (highest first)
        ideas_sorted = sorted(ideas, key=lambda x: x.overall_score, reverse=True)
        
        logger.info(f"Generated {len(ideas_sorted)} ideas, scores: {[f'{i.overall_score:.1f}' for i in ideas_sorted[:5]]}")
        return ideas_sorted
    
    async def _generate_creative_idea(self, business_type: str, trends: List[str]) -> Dict[str, Any]:
        """
        Use LLM to generate a creative business idea.
        
        Args:
            business_type: Type of business (ecommerce, saas, content)
            trends: List of trending categories
        
        Returns:
            Dict with name, description, features, etc.
        """
        prompt = f"""You are a creative business strategist and market analyst.

TASK: Generate a unique, profitable {business_type} business idea.

MARKET CONTEXT:
Current trending categories: {', '.join(trends)}

REQUIREMENTS:
- Must be monetizable within 30 days
- Must be buildable by AI agents (Next.js + TypeScript)
- Must solve a real problem for the target audience
- Must differentiate from existing competitors
- Must have clear revenue model
- Must be scalable (SaaS/automation preferred)

TARGET MARKET:
- B2B SaaS: Small businesses (10-100 employees)
- E-commerce: Online shoppers aged 25-45
- Content: Professionals seeking niche expertise

CREATIVITY RULES:
- Combine trending categories in novel ways
- Focus on underserved niches
- Leverage AI/automation for competitive advantage
- Consider viral/network effects
- Prioritize recurring revenue models

OUTPUT FORMAT (JSON):
{{
    "name": "Short, catchy business name (2-3 words)",
    "business_type": "{business_type}",
    "description": "2-sentence elevator pitch explaining value proposition",
    "target_audience": "Specific audience segment with clear pain point",
    "monetization_model": "Detailed revenue model (pricing, tiers, upsells)",
    "mvp_features": [
        "Feature 1: Must-have core functionality",
        "Feature 2: Key differentiator",
        "Feature 3: Monetization enabler",
        "Feature 4: Viral/growth feature",
        "Feature 5: Retention feature"
    ],
    "tech_stack": ["Next.js 14", "TypeScript", "Vercel", "Stripe", "others..."],
    "success_metrics": {{
        "target_revenue_month_1": "$X",
        "target_users_month_1": "Y users",
        "target_conversion_rate": "Z%"
    }}
}}

Generate a creative, profitable business idea now:"""
        
        try:
            if self.use_anthropic:
                # Use Claude for creative idea generation
                response = await self._call_anthropic(prompt)
            elif self.use_openai:
                # Use GPT-4o for creative idea generation
                response = await self._call_openai(prompt)
            else:
                # Fallback to local LLM (less creative but free)
                response = await self._call_local_llm(prompt)
            
            # Parse JSON response
            idea_data = json.loads(response)
            
            # Ensure business_type is set FIRST (before validation)
            idea_data["business_type"] = business_type
            
            # Validate required fields
            required_fields = ["name", "description", "target_audience", "monetization_model", "mvp_features", "tech_stack"]
            for field in required_fields:
                if field not in idea_data:
                    raise ValueError(f"Missing required field: {field}")
            
            return idea_data
            
        except Exception as e:
            logger.error(f"Failed to generate idea with LLM: {e}")
            # Fallback to template-based idea
            return self._generate_template_idea(business_type, trends)
    
    async def _call_anthropic(self, prompt: str) -> str:
        """Call Claude for idea generation."""
        import anthropic
        
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",  # Claude Sonnet 4 (May 2025 - latest)
            max_tokens=2048,
            temperature=0.9,  # High creativity
            messages=[{"role": "user", "content": prompt}]
        )
        
        response = message.content[0].text
        
        # Extract JSON if wrapped in markdown
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        return response
    
    async def _call_openai(self, prompt: str) -> str:
        """Call GPT-4o for idea generation."""
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a creative business strategist. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=2048
        )
        
        content = response.choices[0].message.content
        
        # Extract JSON if wrapped
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        return content
    
    async def _call_local_llm(self, prompt: str) -> str:
        """Fallback to local LLM (less creative)."""
        from infrastructure.local_llm_client import get_local_llm_client
        
        client = get_local_llm_client()
        # Local LLM may not be as creative, but it's free
        
        # Return a template for now (local LLM JSON generation is unreliable)
        return json.dumps(self._generate_template_idea("ecommerce", []))
    
    def _generate_template_idea(self, business_type: str, trends: List[str]) -> Dict[str, Any]:
        """Fallback template-based idea generation."""
        templates = {
            "ecommerce": {
                "name": f"TrendShop {random.randint(100, 999)}",
                "business_type": business_type,
                "description": f"E-commerce store for {random.choice(trends[:1] or ['trending products'])}. Curated selection with fast shipping.",
                "target_audience": "Online shoppers aged 25-45 seeking quality products",
                "monetization_model": "Product sales with 40% margin, average order value $75",
                "mvp_features": [
                    "Product catalog with 20+ items",
                    "Shopping cart with Stripe checkout",
                    "Order tracking and notifications",
                    "Customer reviews and ratings",
                    "Email marketing for repeat purchases"
                ],
                "tech_stack": ["Next.js 14", "TypeScript", "Stripe", "Vercel", "SendGrid"],
                "success_metrics": {
                    "target_revenue_month_1": "$5,000",
                    "target_users_month_1": "100 users",
                    "target_conversion_rate": "2.5%"
                }
            },
            "saas": {
                "name": f"AutoTool {random.randint(100, 999)}",
                "business_type": business_type,
                "description": "SaaS automation tool for small businesses. Saves 10+ hours/week on repetitive tasks.",
                "target_audience": "Small business owners (10-50 employees) with manual workflows",
                "monetization_model": "Subscription: Free tier (basic), Pro $29/mo, Enterprise $99/mo",
                "mvp_features": [
                    "Automated workflow builder",
                    "Integration with 5+ popular tools",
                    "Team collaboration features",
                    "Analytics dashboard",
                    "API access for power users"
                ],
                "tech_stack": ["Next.js 14", "TypeScript", "Stripe", "Vercel", "PostgreSQL"],
                "success_metrics": {
                    "target_revenue_month_1": "$1,000 MRR",
                    "target_users_month_1": "50 signups",
                    "target_conversion_rate": "10% free-to-paid"
                }
            },
            "content": {
                "name": f"InsightHub {random.randint(100, 999)}",
                "business_type": business_type,
                "description": "Premium content platform with expert insights. Subscription-based access to exclusive articles and courses.",
                "target_audience": "Professionals seeking specialized knowledge in their field",
                "monetization_model": "Subscription: $9/mo for unlimited access, plus premium courses at $49 each",
                "mvp_features": [
                    "Article library with 20+ posts",
                    "Newsletter automation",
                    "Member-only content gating",
                    "Course platform with progress tracking",
                    "Community discussion forum"
                ],
                "tech_stack": ["Next.js 14", "TypeScript", "Stripe", "Vercel", "MDX"],
                "success_metrics": {
                    "target_revenue_month_1": "$500",
                    "target_users_month_1": "100 subscribers",
                    "target_conversion_rate": "5%"
                }
            }
        }
        
        return templates.get(business_type, templates["saas"])
    
    def _score_trend_alignment(self, idea: Dict[str, Any], trends: List[str]) -> float:
        """Score how well idea aligns with current trends."""
        idea_text = f"{idea.get('name', '')} {idea.get('description', '')} {' '.join(idea.get('mvp_features', []))}".lower()
        
        trend_matches = sum(1 for trend in trends if any(word in idea_text for word in trend.lower().split()))
        
        return min(trend_matches * 25, 100)  # Up to 100 if matches 4+ trends
    
    def _score_differentiation(self, idea: Dict[str, Any], market_data: Dict[str, Any]) -> float:
        """Score how differentiated the idea is."""
        # Higher differentiation opportunity = higher score
        diff_opportunity = market_data.get("differentiation_opportunity", 0.5)
        
        # Lower market saturation = higher score
        saturation = market_data.get("market_saturation", 0.5)
        
        return (diff_opportunity * 50) + ((1 - saturation) * 50)


# Singleton
_generator: Optional[BusinessIdeaGenerator] = None


def get_idea_generator() -> BusinessIdeaGenerator:
    """Get or create the global idea generator."""
    global _generator
    if _generator is None:
        _generator = BusinessIdeaGenerator()
    return _generator


if __name__ == "__main__":
    # Test the generator
    import asyncio
    
    async def test():
        generator = BusinessIdeaGenerator()
        
        print("\n" + "="*80)
        print(" "*25 + "Testing Business Idea Generator" + " "*24)
        print("="*80 + "\n")
        
        # Generate one idea
        print("Generating a single business idea...")
        idea = await generator.generate_idea(min_revenue_score=60)
        
        print(f"\n✅ Generated Idea:")
        print(f"  Name: {idea.name}")
        print(f"  Type: {idea.business_type}")
        print(f"  Description: {idea.description}")
        print(f"  Target Audience: {idea.target_audience}")
        print(f"  Monetization: {idea.monetization_model}")
        print(f"\n  Features:")
        for feature in idea.mvp_features:
            print(f"    - {feature}")
        print(f"\n  Scores:")
        print(f"    Revenue Potential: {idea.revenue_score:.1f}/100")
        print(f"    Market Trends: {idea.market_trend_score:.1f}/100")
        print(f"    Differentiation: {idea.differentiation_score:.1f}/100")
        print(f"    OVERALL: {idea.overall_score:.1f}/100")
        
        # Generate batch
        print(f"\n" + "="*80)
        print("Generating batch of 3 ideas...")
        ideas = await generator.generate_batch(count=3, min_revenue_score=60)
        
        print(f"\n✅ Generated {len(ideas)} ideas:")
        for i, idea in enumerate(ideas, 1):
            print(f"\n  {i}. {idea.name} ({idea.business_type}) - Score: {idea.overall_score:.1f}/100")
            print(f"     {idea.description[:100]}...")
    
    asyncio.run(test())

