#!/usr/bin/env python3
"""
Seed Agent-Market platform with Genesis agents (Database-backed version)

This script creates users directly in the database, then creates agents via API.
This bypasses the in-memory auth service limitation.
"""
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import asyncpg
import httpx

# Add testkit to path
testkit_path = Path(__file__).parent.parent / "packages" / "testkit" / "src"
sys.path.insert(0, str(testkit_path))

from agentmarket_testkit.sdk import AgentMarketSDK

# Agent definitions (same as seed_agents.py)
AGENT_DEFINITIONS = [
    {
        "name": "Genesis Meta Agent",
        "file": "genesis_meta_agent.py",
        "description": "Autonomous Business Generation System - Orchestrates all other agents to build complete business solutions from idea to deployment.",
        "categories": ["orchestration", "business", "automation"],
        "tags": ["meta", "orchestrator", "genesis", "autonomous", "business-generation"],
        "pricingModel": "usage-based",
    },
    {
        "name": "Business Idea Generator",
        "file": "business_idea_generator.py",
        "description": "Generates innovative business ideas based on market analysis and trends.",
        "categories": ["ideation", "business", "research"],
        "tags": ["idea", "generation", "business", "innovation"],
        "pricingModel": "subscription",
    },
    {
        "name": "Builder Agent",
        "file": "builder_agent.py",
        "description": "Builds software components and features based on specifications using modern development practices.",
        "categories": ["development", "building", "code-generation"],
        "tags": ["builder", "development", "code", "typescript", "react"],
        "pricingModel": "usage-based",
    },
    {
        "name": "Deploy Agent",
        "file": "deploy_agent.py",
        "description": "Handles deployment of applications to various platforms and cloud services.",
        "categories": ["deployment", "devops", "infrastructure"],
        "tags": ["deploy", "devops", "infrastructure", "cloud"],
        "pricingModel": "usage-based",
    },
    {
        "name": "QA Agent",
        "file": "qa_agent.py",
        "description": "Performs quality assurance testing, validation, and verification of software components.",
        "categories": ["testing", "qa", "validation"],
        "tags": ["qa", "testing", "validation", "quality"],
        "pricingModel": "usage-based",
    },
    {
        "name": "Research Discovery Agent",
        "file": "research_discovery_agent.py",
        "description": "Conducts research and discovery to gather information and insights for projects.",
        "categories": ["research", "discovery", "analysis"],
        "tags": ["research", "discovery", "analysis", "information"],
        "pricingModel": "subscription",
    },
    {
        "name": "Spec Agent",
        "file": "spec_agent.py",
        "description": "Creates detailed specifications and technical documentation for software projects.",
        "categories": ["specification", "documentation", "planning"],
        "tags": ["spec", "specification", "documentation", "planning"],
        "pricingModel": "subscription",
    },
    {
        "name": "Security Agent",
        "file": "security_agent.py",
        "description": "Performs security analysis, vulnerability assessment, and implements security best practices.",
        "categories": ["security", "safety", "compliance"],
        "tags": ["security", "safety", "vulnerability", "compliance"],
        "pricingModel": "usage-based",
    },
    {
        "name": "Maintenance Agent",
        "file": "maintenance_agent.py",
        "description": "Handles ongoing maintenance, updates, and improvements to existing systems.",
        "categories": ["maintenance", "operations", "support"],
        "tags": ["maintenance", "operations", "support", "updates"],
        "pricingModel": "subscription",
    },
    {
        "name": "SEO Agent",
        "file": "seo_agent.py",
        "description": "Optimizes content and websites for search engines to improve visibility and rankings.",
        "categories": ["seo", "marketing", "content"],
        "tags": ["seo", "search", "optimization", "marketing"],
        "pricingModel": "subscription",
    },
    {
        "name": "Content Agent",
        "file": "content_agent.py",
        "description": "Creates and manages content including articles, blog posts, and marketing materials.",
        "categories": ["content", "marketing", "writing"],
        "tags": ["content", "writing", "marketing", "blog"],
        "pricingModel": "subscription",
    },
    {
        "name": "Marketing Agent",
        "file": "marketing_agent.py",
        "description": "Develops and executes marketing strategies, campaigns, and promotional activities.",
        "categories": ["marketing", "promotion", "advertising"],
        "tags": ["marketing", "promotion", "advertising", "campaigns"],
        "pricingModel": "subscription",
    },
    {
        "name": "Support Agent",
        "file": "support_agent.py",
        "description": "Provides customer support, handles tickets, and resolves user issues.",
        "categories": ["support", "customer-service", "helpdesk"],
        "tags": ["support", "customer-service", "helpdesk", "tickets"],
        "pricingModel": "subscription",
    },
    {
        "name": "Analyst Agent",
        "file": "analyst_agent.py",
        "description": "Performs data analysis, generates insights, and creates analytical reports.",
        "categories": ["analytics", "data", "insights"],
        "tags": ["analyst", "analytics", "data", "insights"],
        "pricingModel": "usage-based",
    },
    {
        "name": "Finance Agent",
        "file": "finance_agent.py",
        "description": "Handles financial operations, budgeting, and financial analysis.",
        "categories": ["finance", "accounting", "budgeting"],
        "tags": ["finance", "accounting", "budget", "money"],
        "pricingModel": "subscription",
    },
    {
        "name": "Pricing Agent",
        "file": "pricing_agent.py",
        "description": "Analyzes and optimizes pricing strategies for products and services.",
        "categories": ["pricing", "business", "strategy"],
        "tags": ["pricing", "strategy", "business", "optimization"],
        "pricingModel": "subscription",
    },
    {
        "name": "Email Agent",
        "file": "email_agent.py",
        "description": "Manages email communications, campaigns, and email marketing activities.",
        "categories": ["email", "marketing", "communication"],
        "tags": ["email", "marketing", "communication", "campaigns"],
        "pricingModel": "subscription",
    },
    {
        "name": "Billing Agent",
        "file": "billing_agent.py",
        "description": "Handles billing, invoicing, and payment processing operations.",
        "categories": ["billing", "payments", "finance"],
        "tags": ["billing", "payments", "invoicing", "finance"],
        "pricingModel": "subscription",
    },
    {
        "name": "Commerce Agent",
        "file": "commerce_agent.py",
        "description": "Manages e-commerce operations, product catalogs, and sales processes.",
        "categories": ["commerce", "ecommerce", "sales"],
        "tags": ["commerce", "ecommerce", "sales", "products"],
        "pricingModel": "subscription",
    },
    {
        "name": "Darwin Agent",
        "file": "darwin_agent.py",
        "description": "Evolutionary algorithm agent for optimization and improvement through iterative refinement.",
        "categories": ["optimization", "evolution", "ai"],
        "tags": ["darwin", "evolution", "optimization", "ai"],
        "pricingModel": "usage-based",
    },
    {
        "name": "Domain Name Agent",
        "file": "domain_name_agent.py",
        "description": "Manages domain name registration, DNS configuration, and domain-related operations.",
        "categories": ["infrastructure", "domains", "networking"],
        "tags": ["domain", "dns", "networking", "infrastructure"],
        "pricingModel": "usage-based",
    },
    {
        "name": "Legal Agent",
        "file": "legal_agent.py",
        "description": "Handles legal document analysis, contract review, and compliance checking.",
        "categories": ["legal", "compliance", "documentation"],
        "tags": ["legal", "compliance", "contracts", "documentation"],
        "pricingModel": "subscription",
    },
    {
        "name": "Onboarding Agent",
        "file": "onboarding_agent.py",
        "description": "Manages user onboarding processes and guides new users through setup.",
        "categories": ["onboarding", "user-experience", "support"],
        "tags": ["onboarding", "user-experience", "support", "setup"],
        "pricingModel": "subscription",
    },
    {
        "name": "Reflection Agent",
        "file": "reflection_agent.py",
        "description": "Performs self-reflection and improvement analysis for agent systems.",
        "categories": ["ai", "optimization", "self-improvement"],
        "tags": ["reflection", "ai", "optimization", "self-improvement"],
        "pricingModel": "usage-based",
    },
    {
        "name": "WaltzRL Conversation Agent",
        "file": "waltzrl_conversation_agent.py",
        "description": "Safe conversation agent using WaltzRL safety framework for responsible AI interactions.",
        "categories": ["ai", "safety", "conversation"],
        "tags": ["waltzrl", "safety", "conversation", "ai"],
        "pricingModel": "usage-based",
    },
    {
        "name": "WaltzRL Feedback Agent",
        "file": "waltzrl_feedback_agent.py",
        "description": "Feedback collection and analysis agent using WaltzRL safety framework.",
        "categories": ["ai", "safety", "feedback"],
        "tags": ["waltzrl", "safety", "feedback", "ai"],
        "pricingModel": "usage-based",
    },
    {
        "name": "SE Darwin Agent",
        "file": "se_darwin_agent.py",
        "description": "Software engineering evolutionary agent for code improvement and optimization.",
        "categories": ["development", "optimization", "evolution"],
        "tags": ["darwin", "evolution", "development", "optimization"],
        "pricingModel": "usage-based",
    },
    {
        "name": "Ring1T Reasoning Agent",
        "file": "ring1t_reasoning.py",
        "description": "Advanced reasoning agent using Ring1T framework for complex problem solving.",
        "categories": ["ai", "reasoning", "problem-solving"],
        "tags": ["reasoning", "ai", "problem-solving", "ring1t"],
        "pricingModel": "usage-based",
    },
]


async def ensure_user_in_db(database_url: str, email: str, display_name: str) -> str:
    """Create or get user directly from database"""
    conn = await asyncpg.connect(dsn=database_url)
    try:
        # Try to get existing user
        user = await conn.fetchrow('SELECT id FROM "User" WHERE email = $1', email)
        if user:
            return user["id"]
        
        # Create new user
        user_id = str(uuid4())
        await conn.execute(
            'INSERT INTO "User"(id, email, "displayName", password, "createdAt", "updatedAt") '
            'VALUES($1, $2, $3, $4, NOW(), NOW())',
            user_id,
            email,
            display_name,
            "placeholder-hash",  # Password hash (not used for API auth)
        )
        return user_id
    finally:
        await conn.close()


async def seed_agents():
    """Seed all agents into the Agent-Market platform"""
    api_url = os.getenv("AGENT_MARKET_API_URL", "http://localhost:4000")
    database_url = os.getenv("DATABASE_URL")
    creator_email = os.getenv("SEED_CREATOR_EMAIL", "genesis@swarmsync.ai")
    creator_name = os.getenv("SEED_CREATOR_NAME", "Genesis System")

    log_file = Path(__file__).parent / "seed_log.txt"
    
    def log(msg):
        """Log to both console and file"""
        # Remove emojis for Windows compatibility
        msg_clean = msg.encode('ascii', 'ignore').decode('ascii') if sys.platform == 'win32' else msg
        try:
            print(msg)
        except UnicodeEncodeError:
            print(msg_clean)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')} - {msg}\n")
    
    # Initialize log
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Agent Seeding Log - {datetime.now()}\n")
        f.write("=" * 60 + "\n\n")
    
    log("Seeding agents into Agent-Market...")
    log(f"   API URL: {api_url}")
    log(f"   Creator: {creator_email}\n")

    # Check database URL
    if not database_url:
        log("   ❌ DATABASE_URL environment variable is required")
        log("   Set it in your .env file or export it before running")
        return

    # Get or create user in database
    log("Setting up creator user in database...")
    try:
        creator_id = await ensure_user_in_db(database_url, creator_email, creator_name)
        log(f"   OK User ID: {creator_id}")
    except Exception as e:
        log(f"   ERROR Failed to create/get user: {e}")
        return

    # Test API connection (non-blocking)
    sdk = AgentMarketSDK(base_url=api_url, timeout=30.0)
    api_accessible = False
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{api_url}/agents", timeout=5.0)
                log("   OK API is accessible\n")
                api_accessible = True
            except Exception as e:
                log(f"   WARNING Could not reach API: {e}")
                log(f"   Will attempt to create agents anyway (API may start during seeding)\n")
    except Exception as e:
        log(f"   WARNING API check failed: {e}")
        log(f"   Will attempt to create agents anyway\n")

    # Create all agents
    log(f"\nCreating {len(AGENT_DEFINITIONS)} agents...\n")
    created = 0
    errors = []

    for i, agent_def in enumerate(AGENT_DEFINITIONS, 1):
        agent_name = agent_def["name"]
        log(f"[{i}/{len(AGENT_DEFINITIONS)}] Creating {agent_name}...")

        try:
            payload = {
                "name": agent_name,
                "description": agent_def["description"],
                "categories": agent_def["categories"],
                "tags": agent_def["tags"],
                "pricingModel": agent_def["pricingModel"],
                "visibility": "PUBLIC",
                "creatorId": creator_id,
            }
            
            # After creating, update status to APPROVED via direct DB call
            import asyncpg
            db_conn = await asyncpg.connect(dsn=database_url)
            try:
                # Get the created agent's ID from the response
                agent_id = agent['id']
                # Update status to APPROVED
                await db_conn.execute(
                    'UPDATE "Agent" SET status = $1 WHERE id = $2',
                    'APPROVED',
                    agent_id
                )
                log(f"   OK Status updated to APPROVED")
            finally:
                await db_conn.close()

            # Use SDK method which should handle JSON properly
            agent = await sdk.create_agent(payload)
            agent_id = agent['id']
            
            # Update status to APPROVED via direct DB call
            db_conn = await asyncpg.connect(dsn=database_url)
            try:
                await db_conn.execute(
                    'UPDATE "Agent" SET status = $1 WHERE id = $2',
                    'APPROVED',
                    agent_id
                )
            finally:
                await db_conn.close()
            
            log(f"   OK Created (ID: {agent_id}, Slug: {agent.get('slug', 'N/A')}) - Status: APPROVED")
            created += 1
        except Exception as e:
            # Try to get detailed error from response
            error_msg = str(e)
            error_details = error_msg
            
            # Try to extract error details from httpx exception
            if hasattr(e, 'response'):
                try:
                    if hasattr(e.response, 'read'):
                        error_text = e.response.text if hasattr(e.response, 'text') else str(e.response.read())
                        error_details = f"{error_msg}\n   Response: {error_text[:500]}"
                    elif hasattr(e.response, 'text'):
                        error_details = f"{error_msg}\n   Response: {e.response.text[:500]}"
                except Exception as parse_err:
                    error_details = f"{error_msg} (could not parse response: {parse_err})"
            
            log(f"   ERROR: {error_details[:400]}")
            errors.append((agent_name, error_details))

    log(f"\nSummary:")
    log(f"   Created: {created} agents")
    log(f"   Errors: {len(errors)}")

    if errors:
        log(f"\nErrors encountered:")
        for agent_name, error in errors:
            log(f"   - {agent_name}: {error}")

    log(f"\nSeeding complete!")
    log(f"   Log file: {log_file}")

    await sdk.close()


if __name__ == "__main__":
    asyncio.run(seed_agents())

