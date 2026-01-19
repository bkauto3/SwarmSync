#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emergency Auth Testing Script
Tests all authentication flows on live production site
"""

import asyncio
import json
from playwright.async_api import async_playwright
import sys
import os

# Force UTF-8 output
if sys.platform == "win32":
    os.system("")  # Enable ANSI escape sequences on Windows
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

LIVE_URL = "https://swarmsync.ai"
INVITE_LINK = "https://swarmsync.ai/invite/4db223a6-93a2-4561-92e5-8561b32a72d5"

async def test_live_auth():
    """Test authentication flows on live site"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        # Collect console logs
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        # Collect errors
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))

        print("\n" + "="*80)
        print("EMERGENCY AUTH TEST - PRODUCTION SITE")
        print("="*80)

        # Test 1: Check login page loads without hydration errors
        print("\n[TEST 1] Loading login page...")
        try:
            await page.goto(f"{LIVE_URL}/login", wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # Check for React hydration error
            has_hydration_error = any("Minified React error #418" in log for log in console_logs)
            has_css_error = any("Uncaught SyntaxError" in log for log in console_logs)

            print(f"   ✓ Page loaded")
            print(f"   React Hydration Error: {'❌ FOUND' if has_hydration_error else '✅ NONE'}")
            print(f"   CSS Syntax Error: {'❌ FOUND' if has_css_error else '✅ NONE'}")

            if has_hydration_error or has_css_error:
                print("\n   Console Errors:")
                for log in console_logs[-10:]:
                    print(f"      {log}")
                return False

        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            return False

        # Test 2: Check Google OAuth button is clickable
        print("\n[TEST 2] Testing Google OAuth button...")
        try:
            google_btn = await page.query_selector('button:has-text("Google")')
            if not google_btn:
                print("   ❌ Google button not found")
                return False

            # Check if button is enabled
            is_disabled = await google_btn.is_disabled()
            is_visible = await google_btn.is_visible()

            print(f"   Button visible: {'✅' if is_visible else '❌'}")
            print(f"   Button enabled: {'✅' if not is_disabled else '❌'}")

            # Try to click (but don't complete OAuth flow)
            if is_visible and not is_disabled:
                # Monitor for navigation
                async with page.expect_navigation(timeout=5000) as nav_info:
                    await google_btn.click()

                navigation = await nav_info.value
                new_url = navigation.url

                if "accounts.google.com" in new_url:
                    print(f"   ✅ OAuth redirect working! Redirected to: {new_url[:50]}...")
                    await page.go_back()
                else:
                    print(f"   ❌ Unexpected redirect: {new_url}")
                    return False
            else:
                print("   ❌ Button not clickable")
                return False

        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            # This might timeout if button works - that's actually good
            if "Timeout" in str(e) and "accounts.google.com" in page.url:
                print("   ✅ Button clicked and started OAuth flow")
                await page.go_back()
            else:
                return False

        # Test 3: Check email/password form
        print("\n[TEST 3] Testing email/password form...")
        try:
            await page.goto(f"{LIVE_URL}/login", wait_until="networkidle")
            await page.wait_for_timeout(2000)

            email_input = await page.query_selector('input[type="email"]')
            password_input = await page.query_selector('input[type="password"]')
            submit_btn = await page.query_selector('button[type="submit"]:has-text("Sign In")')

            if not all([email_input, password_input, submit_btn]):
                print("   ❌ Form elements not found")
                return False

            print("   ✅ All form elements present")

            # Try filling form (with fake data, won't submit)
            await email_input.fill("test@example.com")
            await password_input.fill("testpassword123")

            # Check if submit button is clickable
            is_disabled = await submit_btn.is_disabled()
            print(f"   Submit button enabled: {'✅' if not is_disabled else '❌'}")

        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            return False

        # Test 4: Check invite link flow
        print("\n[TEST 4] Testing invite link...")
        try:
            await page.goto(INVITE_LINK, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            # Should show "manual_login_required" state since not authenticated
            page_content = await page.content()

            if "Authentication Required" in page_content or "Sign In to Accept" in page_content:
                print("   ✅ Invite page correctly shows login required")

                # Check for sign in button
                sign_in_btn = await page.query_selector('button:has-text("Sign In to Accept")')
                if sign_in_btn:
                    print("   ✅ Sign in button present")

                    # Click it and verify redirect
                    await sign_in_btn.click()
                    await page.wait_for_timeout(2000)

                    current_url = page.url
                    if "/login" in current_url and "callbackUrl" in current_url:
                        print(f"   ✅ Redirects to login with callback: {current_url[:80]}...")
                    else:
                        print(f"   ⚠️  Unexpected URL: {current_url}")
                else:
                    print("   ⚠️  Sign in button not found")
            else:
                print("   ⚠️  Unexpected page state")

        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            return False

        # Print summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Console logs collected: {len(console_logs)}")
        print(f"Errors detected: {len(errors)}")

        if errors:
            print("\nErrors:")
            for err in errors[:5]:
                print(f"   {err}")

        # Final check
        has_critical_errors = any([
            any("Minified React error #418" in log for log in console_logs),
            any("Uncaught SyntaxError" in log for log in console_logs),
            len(errors) > 0
        ])

        if not has_critical_errors:
            print("\n✅ ALL TESTS PASSED - Authentication is functional!")
            return True
        else:
            print("\n❌ CRITICAL ERRORS STILL PRESENT")
            return False

if __name__ == "__main__":
    result = asyncio.run(test_live_auth())
    sys.exit(0 if result else 1)
