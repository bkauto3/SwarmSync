#!/usr/bin/env python3
"""
Script to set Netlify environment variables via API.
Usage: python set-netlify-env.py <NETLIFY_AUTH_TOKEN>

Get your token from: https://app.netlify.com/user/applications/personal
"""

import sys
import requests
import json

SITE_ID = "dda03034-cd64-41d5-b457-c5d31ae1efda"
NETLIFY_API_BASE = "https://api.netlify.com/api/v1"

# Environment variables to set
ENV_VARS = {
    "NEXTAUTH_SECRET": "HNT0jWSyAGYkf3DAaUgpIUgfJdY7jwMW",
    "NEXTAUTH_URL": "https://swarmsync.ai",
    "GOOGLE_CLIENT_ID": "1056389438638-qjhk5vkfspi742rjg74661crsfeamkOr.apps.googleusercontent.com",
    "GOOGLE_CLIENT_SECRET": "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",
    "GITHUB_CLIENT_ID": "Ov23lijhlbg5GGBJZyqp",
    "GITHUB_CLIENT_SECRET": "9970089f7d6588f60ed8c47b4251840137c6eb73",
    "DATABASE_URL": "postgresql://neondb_owner:npg_v0RtJymP2rcw@ep-cold-butterfly-aenonb7s.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require",
}

def set_env_var(token, key, value):
    """Set a single environment variable via Netlify API."""
    url = f"{NETLIFY_API_BASE}/accounts/-/env"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "key": key,
        "scopes": ["builds", "functions", "runtime", "post-processing"],
        "values": [
            {
                "value": value,
                "context": "production",
            }
        ],
        "is_secret": key.endswith("SECRET") or key == "NEXTAUTH_SECRET" or "PASSWORD" in key or "DATABASE_URL" in key
    }

    # Try to create the variable
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 409:
        # Variable exists, update it instead
        print(f"⚠️  {key} already exists, updating...")
        # Get account slug first
        account_response = requests.get(f"{NETLIFY_API_BASE}/accounts", headers=headers)
        if account_response.status_code != 200:
            print(f"❌ Failed to get accounts: {account_response.text}")
            return False

        accounts = account_response.json()
        if not accounts:
            print("❌ No accounts found")
            return False

        account_slug = accounts[0]["slug"]

        # Update the variable
        update_url = f"{NETLIFY_API_BASE}/accounts/{account_slug}/env/{key}"
        update_payload = {
            "scopes": ["builds", "functions", "runtime", "post-processing"],
            "values": [
                {
                    "value": value,
                    "context": "production",
                }
            ],
            "is_secret": key.endswith("SECRET") or key == "NEXTAUTH_SECRET" or "PASSWORD" in key or "DATABASE_URL" in key
        }

        response = requests.patch(update_url, headers=headers, json=update_payload)

    if response.status_code in [200, 201]:
        print(f"✅ Set {key}")
        return True
    else:
        print(f"❌ Failed to set {key}: {response.status_code} - {response.text}")
        return False

def main():
    if len(sys.argv) < 2:
        print("❌ ERROR: Missing Netlify auth token")
        print("\nUsage: python set-netlify-env.py <NETLIFY_AUTH_TOKEN>")
        print("\nGet your token from: https://app.netlify.com/user/applications/personal")
        print("Create a new Personal Access Token with full access.")
        sys.exit(1)

    token = sys.argv[1]

    print(f"Setting environment variables for site: {SITE_ID}\n")

    success_count = 0
    for key, value in ENV_VARS.items():
        if set_env_var(token, key, value):
            success_count += 1

    print(f"\n✅ Successfully set {success_count}/{len(ENV_VARS)} environment variables")

    if success_count == len(ENV_VARS):
        print("\n🎉 All environment variables set successfully!")
        print("\n⚠️  IMPORTANT: You MUST trigger a new deploy for these to take effect:")
        print("   1. Go to: https://app.netlify.com/sites/swarmsync/deploys")
        print("   2. Click 'Trigger deploy' > 'Clear cache and deploy site'")
        print("   3. Wait for deploy to complete")
        print("   4. Test OAuth login at: https://swarmsync.ai/login")
    else:
        print("\n⚠️  Some variables failed to set. Please check errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
