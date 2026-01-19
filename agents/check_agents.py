#!/usr/bin/env python3
"""
Check if agents exist in the database
"""
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def check_agents():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set")
        return
    
    conn = await asyncpg.connect(dsn=database_url)
    try:
        # Check total agent count
        total = await conn.fetchval('SELECT COUNT(*) FROM "Agent"')
        print(f"Total agents in database: {total}")
        
        # Check agents by status
        by_status = await conn.fetch(
            'SELECT status, COUNT(*) as count FROM "Agent" GROUP BY status'
        )
        print(f"\nAgents by status:")
        for row in by_status:
            print(f"  {row['status']}: {row['count']}")
        
        # Check agents by creator
        by_creator = await conn.fetch(
            'SELECT "creatorId", COUNT(*) as count FROM "Agent" GROUP BY "creatorId"'
        )
        print(f"\nAgents by creator:")
        for row in by_creator:
            print(f"  Creator {row['creatorId'][:8]}...: {row['count']} agents")
        
        # List all agents
        agents = await conn.fetch(
            'SELECT id, name, status, visibility, "creatorId", "createdAt" FROM "Agent" ORDER BY "createdAt" DESC LIMIT 10'
        )
        
        print(f"\nRecent agents (showing up to 10):")
        if agents:
            for agent in agents:
                print(f"  - {agent['name']}")
                print(f"    ID: {agent['id']}")
                print(f"    Status: {agent['status']}, Visibility: {agent['visibility']}")
                print(f"    Creator: {agent['creatorId'][:8]}...")
                print(f"    Created: {agent['createdAt']}")
                print()
        else:
            print("  No agents found!")
            
        # Check the genesis user
        genesis_user = await conn.fetchrow(
            'SELECT id, email, "displayName" FROM "User" WHERE email = $1',
            'genesis@swarmsync.ai'
        )
        if genesis_user:
            print(f"\nGenesis user found:")
            print(f"  ID: {genesis_user['id']}")
            print(f"  Email: {genesis_user['email']}")
            print(f"  Name: {genesis_user['displayName']}")
        else:
            print("\nWARNING: Genesis user not found!")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_agents())

