#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test OAuth Button Click
"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os

if sys.platform == "win32":
    os.system("")
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

async def test_oauth_click():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        print("=" * 80)
        print("OAUTH BUTTON CLICK TEST")
        print("=" * 80)
        print()

        # Navigate to login
        print("1. Navigating to login page...")
        await page.goto("https://swarmsync.ai/login", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        print("   ✓ Page loaded")
        print()

        # Find and click Google button
        print("2. Looking for Google OAuth button...")
        google_btn = page.locator('button:has-text("Google")')

        if await google_btn.count() == 0:
            print("   ✗ Google button NOT FOUND")
            await browser.close()
            return False

        print("   ✓ Google button found")
        print()

        # Check button state
        is_visible = await google_btn.is_visible()
        is_enabled = await google_btn.is_enabled()

        print(f"   Button visible: {is_visible}")
        print(f"   Button enabled: {is_enabled}")
        print()

        if not is_visible or not is_enabled:
            print("   ✗ Button not clickable")
            await browser.close()
            return False

        # Click the button and wait for navigation
        print("3. Clicking Google button...")
        try:
            # Wait for navigation to Google OAuth
            async with page.expect_navigation(timeout=10000) as nav_info:
                await google_btn.click()

            navigation = await nav_info.value
            final_url = navigation.url

            print(f"   ✓ Navigation triggered!")
            print(f"   Final URL: {final_url}")
            print()

            # Check if we're on Google OAuth page
            if "accounts.google.com" in final_url:
                print("✅ SUCCESS! OAuth redirect working correctly")
                print(f"   Redirected to Google OAuth: {final_url[:80]}...")
                await page.screenshot(path="oauth-redirect-success.png")
                print("   Screenshot saved: oauth-redirect-success.png")
                await browser.close()
                return True
            else:
                print(f"⚠️  Unexpected redirect: {final_url}")
                await page.screenshot(path="oauth-redirect-unexpected.png")
                await browser.close()
                return False

        except Exception as e:
            print(f"   ✗ Click failed: {e}")
            await page.screenshot(path="oauth-click-failed.png")
            await browser.close()
            return False

if __name__ == "__main__":
    result = asyncio.run(test_oauth_click())
    sys.exit(0 if result else 1)
