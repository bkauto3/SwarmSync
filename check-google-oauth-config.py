# -*- coding: utf-8 -*-
"""Check what Google OAuth is actually receiving"""
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
from urllib.parse import urlparse, parse_qs

print("=" * 80)
print("GOOGLE OAUTH CONFIGURATION CHECK")
print("=" * 80)
print()

base_url = "https://swarmsync.ai"

# Get CSRF token
csrf_response = requests.get(f"{base_url}/api/auth/csrf", timeout=10)
csrf_token = csrf_response.json().get('csrfToken', '')

# Try to initiate Google OAuth and capture the redirect
print("[Step 1] Initiating Google OAuth flow...")
response = requests.get(
    f"{base_url}/api/auth/signin/google",
    params={'callbackUrl': f'{base_url}/dashboard'},
    allow_redirects=False,
    timeout=10
)

print(f"Status: {response.status_code}")
location = response.headers.get('Location', '')
print(f"Redirect Location: {location}")
print()

# Parse the redirect URL
if location:
    parsed = urlparse(location)
    query_params = parse_qs(parsed.query)

    print("[Step 2] Analyzing redirect...")
    print(f"Redirect host: {parsed.netloc}")
    print(f"Redirect path: {parsed.path}")
    print()

    if 'error' in query_params:
        print(f"❌ ERROR DETECTED: {query_params['error']}")
        print()
        print("This means NextAuth encountered an error before even redirecting to Google.")
        print("Possible causes:")
        print("1. Google Client ID is invalid or doesn't match")
        print("2. Google Client Secret is invalid")
        print("3. Redirect URI not configured in Google Cloud Console")
        print("4. OAuth consent screen not configured")
        print()
    elif 'accounts.google.com' in parsed.netloc:
        print("✓ OAuth redirect URL generated successfully")
        print()
        print("Google OAuth parameters:")
        for key, value in query_params.items():
            if key == 'redirect_uri':
                print(f"  {key}: {value[0]}")
                print(f"  ⚠️  THIS MUST BE CONFIGURED IN GOOGLE CLOUD CONSOLE")
            elif key in ['client_id', 'scope', 'response_type']:
                print(f"  {key}: {value[0] if value else 'MISSING'}")
        print()

# Check what the actual Google provider configuration looks like
print("[Step 3] Checking providers configuration...")
providers_response = requests.get(f"{base_url}/api/auth/providers", timeout=10)
providers = providers_response.json()

if 'google' in providers:
    google_config = providers['google']
    print("Google provider config:")
    print(json.dumps(google_config, indent=2))
    print()

print("=" * 80)
print("REQUIRED GOOGLE CLOUD CONSOLE CONFIGURATION")
print("=" * 80)
print()
print("1. Go to: https://console.cloud.google.com/apis/credentials")
print("2. Find your OAuth 2.0 Client ID")
print("3. Under 'Authorized redirect URIs', ensure you have:")
print(f"   https://swarmsync.ai/api/auth/callback/google")
print()
print("4. OAuth consent screen must be configured")
print("5. Required scopes: email, profile, openid")
print()
