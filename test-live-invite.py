# -*- coding: utf-8 -*-
"""Test the actual live invite link provided by the user"""
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright
import time

INVITE_URL = "https://swarmsync.ai/invite/4db223a6-93a2-4561-92e5-8561b32a72d5"

print("=" * 80)
print("EMERGENCY TEST: Live Invite Link Diagnosis")
print("=" * 80)
print()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
    context = browser.new_context()
    page = context.new_page()

    # Collect all console messages
    console_messages = []
    page.on('console', lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))

    # Collect errors
    page.on('pageerror', lambda exc: print(f"❌ PAGE ERROR: {exc}"))

    # Collect failed requests
    def handle_response(response):
        if response.status >= 400:
            print(f"❌ FAILED REQUEST: {response.status} {response.url}")

    page.on('response', handle_response)

    print(f"[Step 1] Navigating to invite link: {INVITE_URL}")
    print()

    try:
        page.goto(INVITE_URL, timeout=30000)
        page.wait_for_load_state('networkidle', timeout=10000)
        time.sleep(3)

        current_url = page.url
        print(f"✓ Current URL: {current_url}")
        print()

        # Take screenshot
        page.screenshot(path='emergency-test-1-initial.png')

        # Check console logs
        print("=" * 80)
        print("CONSOLE LOGS:")
        print("=" * 80)
        for msg in console_messages:
            print(msg)
        print()

        # Check page text
        page_text = page.locator('body').inner_text()
        print("=" * 80)
        print("PAGE TEXT:")
        print("=" * 80)
        print(page_text[:500])
        print()

        # Check if on manual login screen
        if 'Authentication Required' in page_text:
            print("⚠️  SHOWING MANUAL LOGIN SCREEN")
            print()

            # Click Sign In button
            print("[Step 2] Clicking 'Sign In to Accept' button...")
            sign_in_btn = page.locator('button:has-text("Sign In to Accept")')
            if sign_in_btn.count() > 0:
                sign_in_btn.click()
                page.wait_for_load_state('networkidle', timeout=10000)
                time.sleep(2)

                current_url = page.url
                print(f"✓ Redirected to: {current_url}")
                page.screenshot(path='emergency-test-2-login-page.png')
                print()

        # If on login page, try to click Google button
        if '/login' in page.url:
            print("[Step 3] On login page, looking for Google button...")
            print()

            time.sleep(2)

            # Check for Google button
            google_btn = page.locator('button:has-text("Google")')
            if google_btn.count() > 0:
                print(f"✓ Found {google_btn.count()} Google button(s)")

                # Get button HTML
                try:
                    btn_html = google_btn.first.evaluate('el => el.outerHTML')
                    print(f"Button HTML: {btn_html[:200]}")
                except:
                    pass

                print()
                print("[Step 4] Clicking Google button...")
                google_btn.first.click()

                # Wait to see what happens
                print("Waiting 10 seconds to see response...")
                time.sleep(10)

                current_url = page.url
                print(f"✓ Current URL after click: {current_url}")
                page.screenshot(path='emergency-test-3-after-google-click.png')

                if 'google.com' in current_url or 'accounts.google' in current_url:
                    print("✅ GOOGLE OAUTH INITIATED - Redirected to Google")
                elif current_url == page.url:
                    print("❌ NOTHING HAPPENED - Still on same page")
                else:
                    print(f"⚠️  Redirected to: {current_url}")
            else:
                print("❌ NO GOOGLE BUTTON FOUND")

        print()
        print("=" * 80)
        print("FINAL CONSOLE LOGS:")
        print("=" * 80)
        for msg in console_messages[-20:]:
            print(msg)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("Test complete. Check screenshots for visual state.")
    input("Press Enter to close browser...")
    browser.close()
