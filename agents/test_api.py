#!/usr/bin/env python3
"""Test API call to see exact error"""
import asyncio
import httpx

async def test():
    api_url = "http://localhost:4000"
    creator_id = "73ff1ca7-59a0-4414-bf1f-56b40339f843"
    
    payload = {
        "name": "Test Agent",
        "description": "This is a test agent description that is long enough to meet the 10 character minimum requirement",
        "categories": ["test"],
        "tags": ["test"],
        "pricingModel": "subscription",
        "visibility": "PUBLIC",
        "creatorId": creator_id,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{api_url}/agents",
            json=payload,
            timeout=30.0,
        )
        print(f"Status: {response.status_code}")
        print(f"Response text: {response.text}")
        try:
            print(f"Response JSON: {response.json()}")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test())

