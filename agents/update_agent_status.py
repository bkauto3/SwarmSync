#!/usr/bin/env python3
"""
Update all seeded agents from DRAFT to APPROVED status
"""
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def update_agent_status():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set")
        return
    
    conn = await asyncpg.connect(dsn=database_url)
    try:
        creator_id = '73ff1ca7-59a0-4414-bf1f-56b40339f843'
        
        # Get or create 'genesis' organization
        org = await conn.fetchrow(
            'SELECT id FROM "Organization" WHERE slug = $1',
            'genesis'
        )
        
        if not org:
            # Create genesis organization
            org_id = await conn.fetchval(
                'INSERT INTO "Organization"(name, slug) VALUES($1, $2) RETURNING id',
                'Genesis',
                'genesis'
            )
            print(f"Created organization 'genesis' with ID: {org_id}")
        else:
            org_id = org['id']
            print(f"Found organization 'genesis' with ID: {org_id}")
        
        # Update all agents created by the genesis user to APPROVED and assign to organization
        result = await conn.execute(
            'UPDATE "Agent" SET status = $1, "organizationId" = $2 WHERE "creatorId" = $3',
            'APPROVED',
            org_id,
            creator_id
        )
        
        # Get count of updated agents
        count = await conn.fetchval(
            'SELECT COUNT(*) FROM "Agent" WHERE status = $1 AND "creatorId" = $2',
            'APPROVED',
            creator_id
        )
        
        print(f"OK Updated {count} agents to APPROVED status and assigned to organization")
        
        # List all agents
        agents = await conn.fetch(
            'SELECT name, status, visibility, "organizationId" FROM "Agent" WHERE "creatorId" = $1 ORDER BY name',
            creator_id
        )
        
        print(f"\nAgent Status Summary ({len(agents)} total):")
        for agent in agents[:10]:  # Show first 10
            org_status = "has org" if agent['organizationId'] else "no org"
            print(f"   - {agent['name']}: {agent['status']} ({agent['visibility']}) - {org_status}")
        if len(agents) > 10:
            print(f"   ... and {len(agents) - 10} more")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(update_agent_status())

