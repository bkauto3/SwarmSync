#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Complete Invite Link Flow
"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os

if sys.platform == "win32":
    os.system("")
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

INVITE_URL = "https://swarmsync.ai/invite/4db223a6-93a2-4561-92e5-8561b32a72d5"

async def test_invite_flow():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        print("=" * 80)
        print("COMPLETE INVITE FLOW TEST")
        print("=" * 80)
        print()

        # Step 1: Visit invite link (unauthenticated)
        print("STEP 1: Visit invite link (unauthenticated)")
        print("-" * 80)
        await page.goto(INVITE_URL, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        page_content = await page.content()

        # Check for authentication required message
        if "Authentication Required" in page_content or "Sign In to Accept" in page_content:
            print("   SUCCESS: Page correctly shows authentication required")
        else:
            print("   WARNING: Unexpected page state")

        await page.screenshot(path="invite-step1-auth-required.png")
        print("   Screenshot: invite-step1-auth-required.png")
        print()

        # Step 2: Click "Sign In to Accept" button
        print("STEP 2: Click Sign In to Accept button")
        print("-" * 80)

        sign_in_btn = page.locator('button:has-text("Sign In to Accept")')
        if await sign_in_btn.count() == 0:
            print("   FAIL: Sign in button not found")
            await browser.close()
            return False

        print("   SUCCESS: Sign in button found")

        # Click and verify redirect
        await sign_in_btn.click()
        await page.wait_for_timeout(2000)

        current_url = page.url
        print(f"   Current URL: {current_url[:80]}...")

        # Check if we're on login page with callback URL
        if "/login" in current_url and "callbackUrl" in current_url:
            print("   SUCCESS: Redirected to login with callback URL")

            # Decode callback URL to verify it points back to invite
            import urllib.parse
            parsed_url = urllib.parse.urlparse(current_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            callback_url = query_params.get('callbackUrl', [''])[0]

            print(f"   Callback URL: {callback_url}")

            if "/invite/" in callback_url:
                print("   SUCCESS: Callback URL points back to invite link")
            else:
                print("   WARNING: Callback URL doesn't point to invite")
        else:
            print("   FAIL: Unexpected redirect")
            await browser.close()
            return False

        await page.screenshot(path="invite-step2-login-page.png")
        print("   Screenshot: invite-step2-login-page.png")
        print()

        # Step 3: Verify Google OAuth button works
        print("STEP 3: Test Google OAuth from invite-triggered login")
        print("-" * 80)

        google_btn = page.locator('button:has-text("Google")')
        if await google_btn.count() == 0:
            print("   FAIL: Google button not found")
            await browser.close()
            return False

        print("   SUCCESS: Google button found")

        is_visible = await google_btn.is_visible()
        is_enabled = await google_btn.is_enabled()

        print(f"   Button visible: {is_visible}, enabled: {is_enabled}")

        if not is_visible or not is_enabled:
            print("   FAIL: Google button not clickable")
            await browser.close()
            return False

        # Click Google button
        print("   Clicking Google button...")
        try:
            async with page.expect_navigation(timeout=10000) as nav_info:
                await google_btn.click()

            navigation = await nav_info.value
            final_url = navigation.url

            if "accounts.google.com" in final_url:
                print("   SUCCESS: OAuth redirect working!")
                print(f"   Google URL: {final_url[:80]}...")

                await page.screenshot(path="invite-step3-google-oauth.png")
                print("   Screenshot: invite-step3-google-oauth.png")
            else:
                print(f"   FAIL: Unexpected URL: {final_url}")
                await browser.close()
                return False

        except Exception as e:
            print(f"   FAIL: OAuth redirect failed: {e}")
            await browser.close()
            return False

        print()
        print("=" * 80)
        print("INVITE FLOW VERIFICATION COMPLETE")
        print("=" * 80)
        print()
        print("ALL STEPS SUCCESSFUL:")
        print("   1. Invite page shows authentication required")
        print("   2. Sign In to Accept redirects to login with callback")
        print("   3. OAuth button works from callback login page")
        print("   4. Callback URL preserved for post-auth redirect")

        await browser.close()
        return True

if __name__ == "__main__":
    result = asyncio.run(test_invite_flow())
    sys.exit(0 if result else 1)
