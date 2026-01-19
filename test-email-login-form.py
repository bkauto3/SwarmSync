#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Email/Password Login Form
"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os

if sys.platform == "win32":
    os.system("")
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

async def test_email_form():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        print("=" * 80)
        print("EMAIL/PASSWORD FORM TEST")
        print("=" * 80)
        print()

        # Navigate to login
        print("1. Navigating to login page...")
        await page.goto("https://swarmsync.ai/login", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        print("   ✓ Page loaded")
        print()

        # Find form elements
        print("2. Locating form elements...")
        email_input = page.locator('input[type="email"]')
        password_input = page.locator('input[type="password"]')
        submit_btn = page.locator('button[type="submit"]:has-text("Sign In")')

        email_count = await email_input.count()
        password_count = await password_input.count()
        submit_count = await submit_btn.count()

        print(f"   Email input found: {email_count > 0}")
        print(f"   Password input found: {password_count > 0}")
        print(f"   Submit button found: {submit_count > 0}")
        print()

        if email_count == 0 or password_count == 0 or submit_count == 0:
            print("   ✗ Form elements missing")
            await browser.close()
            return False

        # Check form element states
        print("3. Checking form element states...")
        email_visible = await email_input.is_visible()
        email_enabled = await email_input.is_enabled()
        password_visible = await password_input.is_visible()
        password_enabled = await password_input.is_enabled()
        submit_visible = await submit_btn.is_visible()
        submit_enabled = await submit_btn.is_enabled()

        print(f"   Email: visible={email_visible}, enabled={email_enabled}")
        print(f"   Password: visible={password_visible}, enabled={password_enabled}")
        print(f"   Submit: visible={submit_visible}, enabled={submit_enabled}")
        print()

        if not all([email_visible, email_enabled, password_visible, password_enabled, submit_visible, submit_enabled]):
            print("   ✗ Some form elements not interactive")
            await browser.close()
            return False

        # Try filling form (with test data - won't actually submit)
        print("4. Testing form input...")
        await email_input.fill("test@example.com")
        await password_input.fill("testpassword123")

        # Get input values to verify they were filled
        email_value = await email_input.input_value()
        password_value = await password_input.input_value()

        print(f"   Email filled: {email_value == 'test@example.com'}")
        print(f"   Password filled: {len(password_value) > 0}")
        print()

        # Check if submit button is still enabled after filling
        submit_still_enabled = await submit_btn.is_enabled()
        print(f"   Submit button still enabled: {submit_still_enabled}")
        print()

        # Take screenshot
        await page.screenshot(path="email-form-filled.png")
        print("   Screenshot saved: email-form-filled.png")
        print()

        await browser.close()

        if all([
            email_visible, email_enabled,
            password_visible, password_enabled,
            submit_visible, submit_enabled, submit_still_enabled,
            email_value == 'test@example.com',
            len(password_value) > 0
        ]):
            print("✅ SUCCESS! Email/password form is fully functional")
            return True
        else:
            print("⚠️  Some form functionality issues detected")
            return False

if __name__ == "__main__":
    result = asyncio.run(test_email_form())
    sys.exit(0 if result else 1)
