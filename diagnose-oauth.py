# -*- coding: utf-8 -*-
"""Direct diagnosis of what's breaking OAuth"""
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import json

print("=" * 80)
print("DIRECT OAUTH DIAGNOSIS")
print("=" * 80)
print()

base_url = "https://swarmsync.ai"

# Test 1: Check NextAuth providers endpoint
print("[Test 1] Checking NextAuth providers endpoint...")
try:
    response = requests.get(f"{base_url}/api/auth/providers", timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        providers = response.json()
        print(f"✓ Providers available: {list(providers.keys())}")
        print(f"  Google configured: {'google' in providers}")
        print(f"  GitHub configured: {'github' in providers}")
        print()
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        print()
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()

# Test 2: Check NextAuth signin/google endpoint
print("[Test 2] Checking Google signin endpoint...")
try:
    response = requests.get(
        f"{base_url}/api/auth/signin/google",
        allow_redirects=False,
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(f"Location header: {response.headers.get('Location', 'NOT SET')}")

    if response.status_code == 302 or response.status_code == 307:
        location = response.headers.get('Location', '')
        if 'accounts.google.com' in location:
            print("✓ Correctly redirects to Google OAuth")
        elif 'error=' in location:
            print(f"❌ Redirects with error: {location}")
        else:
            print(f"⚠️  Redirects to: {location}")
    else:
        print(f"❌ Expected 302/307 redirect, got {response.status_code}")
        print(f"Response: {response.text[:500]}")
    print()
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()

# Test 3: Check CSRF token endpoint
print("[Test 3] Checking CSRF token endpoint...")
try:
    response = requests.get(f"{base_url}/api/auth/csrf", timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        csrf_data = response.json()
        print(f"✓ CSRF token received: {csrf_data.get('csrfToken', 'MISSING')[:20]}...")
        print()
    else:
        print(f"❌ Failed: {response.status_code}")
        print()
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()

# Test 4: Check session endpoint
print("[Test 4] Checking session endpoint...")
try:
    response = requests.get(f"{base_url}/api/auth/session", timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        session = response.json()
        print(f"Session data: {json.dumps(session, indent=2)}")
        print()
    else:
        print(f"❌ Failed: {response.status_code}")
        print()
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()

# Test 5: Simulate NextAuth signIn POST request
print("[Test 5] Simulating NextAuth signIn POST...")
try:
    # Get CSRF token first
    csrf_response = requests.get(f"{base_url}/api/auth/csrf", timeout=10)
    csrf_token = csrf_response.json().get('csrfToken', '')

    # POST to signin endpoint like NextAuth client does
    response = requests.post(
        f"{base_url}/api/auth/signin/google",
        data={
            'csrfToken': csrf_token,
            'callbackUrl': '/invite/test-token',
            'json': 'true'
        },
        allow_redirects=False,
        timeout=10
    )

    print(f"Status: {response.status_code}")
    print(f"Location header: {response.headers.get('Location', 'NOT SET')}")

    if response.status_code in [302, 307]:
        location = response.headers.get('Location', '')
        if 'accounts.google.com' in location:
            print("✓ POST correctly initiates Google OAuth")
            print(f"  OAuth URL: {location[:100]}...")
        else:
            print(f"⚠️  Redirects to: {location}")
    else:
        print(f"Response body: {response.text[:500]}")

    print()
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()

print("=" * 80)
print("DIAGNOSIS COMPLETE")
print("=" * 80)
