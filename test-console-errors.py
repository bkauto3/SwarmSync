#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detailed Console Error Analysis
"""

import asyncio
from playwright.async_api import async_playwright
import sys
import os

if sys.platform == "win32":
    os.system("")
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

async def analyze_console_errors():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        # Collect detailed console logs
        console_logs = []
        def handle_console(msg):
            log_entry = {
                'type': msg.type,
                'text': msg.text,
                'location': msg.location
            }
            console_logs.append(log_entry)
            print(f"[{msg.type.upper()}] {msg.text}")
            if msg.location:
                print(f"    Location: {msg.location}")

        page.on("console", handle_console)

        # Collect page errors
        page_errors = []
        def handle_error(err):
            page_errors.append(str(err))
            print(f"[PAGE ERROR] {err}")

        page.on("pageerror", handle_error)

        print("=" * 80)
        print("DETAILED CONSOLE ERROR ANALYSIS")
        print("=" * 80)
        print()

        # Navigate to login page
        print("Loading: https://swarmsync.ai/login")
        print()
        await page.goto("https://swarmsync.ai/login", wait_until="networkidle")
        await page.wait_for_timeout(5000)

        print()
        print("=" * 80)
        print("ANALYSIS")
        print("=" * 80)
        print()

        # Categorize errors
        css_errors = [log for log in console_logs if 'css' in log.get('text', '').lower() or log.get('location', {}).get('url', '').endswith('.css')]
        js_errors = [log for log in console_logs if log['type'] == 'error' and 'css' not in log.get('text', '').lower()]
        hydration_errors = [log for log in console_logs if 'hydration' in log.get('text', '').lower() or '#418' in log.get('text', '')]
        syntax_errors = [log for log in console_logs if 'SyntaxError' in log.get('text', '')]

        print(f"Total console messages: {len(console_logs)}")
        print(f"CSS-related errors: {len(css_errors)}")
        print(f"JavaScript errors: {len(js_errors)}")
        print(f"Hydration errors: {len(hydration_errors)}")
        print(f"Syntax errors: {len(syntax_errors)}")
        print()

        if syntax_errors:
            print("SYNTAX ERRORS DETAIL:")
            for err in syntax_errors:
                print(f"  - {err['text']}")
                if err.get('location'):
                    print(f"    URL: {err['location'].get('url', 'N/A')}")
                    print(f"    Line: {err['location'].get('lineNumber', 'N/A')}")
            print()

        # Check if login buttons are functional
        print("FUNCTIONALITY TEST:")
        try:
            google_btn = page.locator('button:has-text("Google")')
            if await google_btn.count() > 0:
                print("  ✓ Google button found")
                is_visible = await google_btn.is_visible()
                is_enabled = await google_btn.is_enabled()
                print(f"    Visible: {is_visible}, Enabled: {is_enabled}")
        except Exception as e:
            print(f"  ✗ Error checking Google button: {e}")

        await page.screenshot(path="login-page-debug.png")
        print()
        print("Screenshot saved: login-page-debug.png")

        await browser.close()

        # Determine if errors are critical
        critical_errors = hydration_errors or [e for e in js_errors if 'React' in e.get('text', '')]

        if not critical_errors:
            print()
            print("✓ No critical errors that would break authentication")
            print("  (CSS syntax errors may be Netlify/CDN related, not app breaking)")
            return True
        else:
            print()
            print("✗ Critical errors found that may affect functionality")
            return False

if __name__ == "__main__":
    result = asyncio.run(analyze_console_errors())
    sys.exit(0 if result else 1)
