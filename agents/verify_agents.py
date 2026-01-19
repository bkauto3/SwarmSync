#!/usr/bin/env python3
"""
Verify agents exist in the database and show connection details
"""
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def verify():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return
    
    # Extract database name from URL for display
    db_name = database_url.split('/')[-1].split('?')[0] if '/' in database_url else 'unknown'
    print(f"Connecting to database: {db_name}")
    print(f"Connection string: {database_url[:50]}...")
    print()
    
    conn = await asyncpg.connect(dsn=database_url)
    try:
        # Get database name
        db_info = await conn.fetchval('SELECT current_database()')
        print(f"Connected to database: {db_info}")
        
        # Get schema
        schema = await conn.fetchval('SELECT current_schema()')
        print(f"Current schema: {schema}")
        print()
        
        # Check total agents
        total = await conn.fetchval('SELECT COUNT(*) FROM "Agent"')
        print(f"Total agents in Agent table: {total}")
        
        if total == 0:
            print("\nWARNING: No agents found!")
            print("Checking if table exists...")
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'Agent'
                )
            """)
            print(f"Agent table exists: {table_exists}")
            
            # Check other tables
            all_tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            print(f"\nTables in public schema ({len(all_tables)} total):")
            for table in all_tables[:10]:
                print(f"  - {table['table_name']}")
        else:
            # Show agents by status
            by_status = await conn.fetch(
                'SELECT status, COUNT(*) as count FROM "Agent" GROUP BY status ORDER BY count DESC'
            )
            print(f"\nAgents by status:")
            for row in by_status:
                print(f"  {row['status']}: {row['count']}")
            
            # Show recent agents
            agents = await conn.fetch(
                'SELECT name, status, visibility, "createdAt" FROM "Agent" ORDER BY "createdAt" DESC LIMIT 5'
            )
            print(f"\nMost recent agents:")
            for agent in agents:
                print(f"  - {agent['name']} ({agent['status']}, {agent['visibility']})")
                print(f"    Created: {agent['createdAt']}")
        
        # Check genesis user
        genesis = await conn.fetchrow(
            'SELECT id, email FROM "User" WHERE email = $1',
            'genesis@swarmsync.ai'
        )
        if genesis:
            print(f"\nGenesis user found: {genesis['email']} (ID: {genesis['id'][:8]}...)")
        else:
            print("\nWARNING: Genesis user not found!")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(verify())

