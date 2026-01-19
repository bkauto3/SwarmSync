#!/usr/bin/env python3
"""
Simple wrapper to seed agents - loads DATABASE_URL from .env automatically
"""
import os
import sys
from pathlib import Path

# Try to load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env from {env_path}")
    else:
        print(f"⚠️  .env file not found at {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed, using environment variables only")
    print("   Install with: pip install python-dotenv")

# Check if DATABASE_URL is set
if not os.getenv("DATABASE_URL"):
    print("\n❌ DATABASE_URL is not set!")
    print("   Set it in your .env file or export it:")
    print("   export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname")
    print("\n   Or add it to .env file in the project root")
    sys.exit(1)

print(f"✅ DATABASE_URL is set")
print(f"   API URL: {os.getenv('AGENT_MARKET_API_URL', 'http://localhost:4000')}")
print()

# Import and run the seeding script
from seed_agents_db import seed_agents
import asyncio

if __name__ == "__main__":
    asyncio.run(seed_agents())

