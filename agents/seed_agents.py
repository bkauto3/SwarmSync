#!/usr/bin/env python3
"""
Seed Agent-Market platform with Genesis agents

This script creates all migrated agents in the Agent-Market platform.

Usage:
    # Make sure API is running first
    npm run dev --workspace @agent-market/api

    # Then run the seeding script
    python seed_agents.py

    # Or with custom settings:
    AGENT_MARKET_API_URL=http://localhost:4000 python seed_agents.py
"""
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add testkit to path
testkit_path = Path(__file__).parent.parent / "packages" / "testkit" / "src"
sys.path.insert(0, str(testkit_path))

from agentmarket_testkit.sdk import AgentMarketSDK
from agentmarket_testkit.utils import unique_agent_name

# Agent definitions with metadata
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


async def seed_agents():
    """Seed all agents into the Agent-Market platform"""
    api_url = os.getenv("AGENT_MARKET_API_URL", "http://localhost:4000")
    creator_email = os.getenv("SEED_CREATOR_EMAIL", "genesis@swarmsync.ai")
    creator_password = os.getenv("SEED_CREATOR_PASSWORD", "GenesisSeed123!")
    creator_name = os.getenv("SEED_CREATOR_NAME", "Genesis System")

    log_file = Path(__file__).parent / "seed_log.txt"
    
    def log(msg):
        """Log to both console and file"""
        print(msg)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')} - {msg}\n")
    
    # Initialize log
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"Agent Seeding Log - {datetime.now()}\n")
        f.write("=" * 60 + "\n\n")
    
    log(f"🌱 Seeding agents into Agent-Market...")
    log(f"   API URL: {api_url}")
    log(f"   Creator: {creator_email}\n")

    sdk = AgentMarketSDK(base_url=api_url, timeout=30.0)
    
    # Test API connection
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{api_url}/health", timeout=5.0)
                if response.status_code == 200:
                    log("   ✅ API is accessible\n")
                else:
                    log(f"   ⚠️  API returned status {response.status_code}\n")
            except httpx.RequestError:
                # Try agents endpoint instead
                response = await client.get(f"{api_url}/agents", timeout=5.0)
                log("   ✅ API is accessible (via /agents endpoint)\n")
    except Exception as e:
        log(f"   ⚠️  Could not reach API at {api_url}: {e}")
        log(f"   Make sure the API is running: npm run dev --workspace @agent-market/api\n")
        return

    try:
        # Create or login as creator user
        log("👤 Setting up creator user...")
        creator_id = None
        
        # Try to register first
        try:
            response = await sdk.register_user(
                email=creator_email,
                display_name=creator_name,
                password=creator_password,
            )
            creator_id = response["user"]["id"]
            log(f"   ✅ Created user: {creator_id}")
        except Exception as e:
            # Get detailed error info
            error_details = str(e)
            if hasattr(e, 'response') and hasattr(e.response, 'json'):
                try:
                    error_body = e.response.json()
                    error_details = f"{error_details} - {error_body}"
                except:
                    pass
            
            log(f"   ⚠️  Registration failed: {error_details}")
            
            # User might already exist, try to login
            log("   Attempting to login as existing user...")
            try:
                response = await sdk.login(email=creator_email, password=creator_password)
                creator_id = response["user"]["id"]
                log(f"   ✅ Logged in as existing user: {creator_id}")
            except Exception as login_error:
                login_details = str(login_error)
                if hasattr(login_error, 'response') and hasattr(login_error.response, 'json'):
                    try:
                        error_body = login_error.response.json()
                        login_details = f"{login_details} - {error_body}"
                    except:
                        pass
                
                log(f"   ❌ Failed to login: {login_details}")
                log(f"\n   💡 Tip: You may need to create the user manually first via the web interface")
                log(f"   Or check if the API is using a different auth system (database-backed vs in-memory)")
                return
        
        if not creator_id:
            log("   ❌ Could not obtain creator ID")
            return

        # Create all agents
        log(f"\n📦 Creating {len(AGENT_DEFINITIONS)} agents...\n")
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

                agent = await sdk.create_agent(payload)
                log(f"   ✅ Created (ID: {agent['id']})")
                created += 1
            except Exception as e:
                error_msg = str(e)[:200]
                log(f"   ❌ Error: {error_msg}")
                errors.append((agent_name, error_msg))

        log(f"\n📊 Summary:")
        log(f"   ✅ Created: {created} agents")
        log(f"   ❌ Errors: {len(errors)}")

        if errors:
            log(f"\n⚠️  Errors encountered:")
            for agent_name, error in errors:
                log(f"   - {agent_name}: {error}")

        log(f"\n✅ Seeding complete!")
        log(f"   Log file: {log_file}")

    finally:
        await sdk.close()


if __name__ == "__main__":
    asyncio.run(seed_agents())

