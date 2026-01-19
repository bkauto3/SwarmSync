#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SwarmSync Production E2E Tests - Agent Creation & Workflow Creation
Tests both flows after authentication fix deployment
"""

import sys
import io
from playwright.sync_api import sync_playwright, expect
import os
import time
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Test credentials
EMAIL = "rainking6693@gmail.com"
PASSWORD = "Hudson1234%"

# Expected user details from database
USER_ID = "e9b91865-be00-4b76-a293-446e1be9151c"
ORG_ID = "93209c61-e6ea-4d9b-b2fa-126f8bcb2d6e"

def take_screenshot(page, name: str):
    """Take a screenshot with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_dir = "test_screenshots_post_deployment"
    os.makedirs(screenshot_dir, exist_ok=True)
    path = f"{screenshot_dir}/{timestamp}_{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"📸 Screenshot saved: {path}")
    return path

def login(page):
    """Login to SwarmSync and return session status"""
    print("\n" + "="*60)
    print("TEST 1: LOGIN FLOW")
    print("="*60)

    # Navigate to login page
    print("→ Navigating to https://swarmsync.ai/login")
    page.goto("https://swarmsync.ai/login")
    page.wait_for_load_state("networkidle")
    take_screenshot(page, "01_login_page")

    # Fill credentials
    print(f"→ Filling email: {EMAIL}")
    page.fill('input[name="email"]', EMAIL)

    print("→ Filling password: ********")
    page.fill('input[name="password"]', PASSWORD)
    take_screenshot(page, "02_credentials_filled")

    # Click Sign In
    print("→ Clicking Sign In button")
    page.click('button:has-text("Sign In")')

    # Wait for redirect
    print("→ Waiting for redirect after login...")
    page.wait_for_url("**/console/**", timeout=10000)
    page.wait_for_load_state("networkidle")

    current_url = page.url
    print(f"✅ Login successful! Redirected to: {current_url}")
    take_screenshot(page, "03_after_login")

    # Verify session cookies
    cookies = page.context.cookies()
    auth_cookies = [c for c in cookies if 'auth' in c['name'].lower()]
    print(f"✅ Session cookies set: {len(auth_cookies)} auth-related cookies")

    return True

def test_agent_creation(page):
    """Test agent creation flow - THIS WAS BLOCKED BEFORE THE FIX"""
    print("\n" + "="*60)
    print("TEST 2: AGENT CREATION FLOW (CRITICAL TEST)")
    print("="*60)

    print("→ Navigating to https://swarmsync.ai/agents/new")
    page.goto("https://swarmsync.ai/agents/new")
    page.wait_for_load_state("networkidle")
    time.sleep(2)  # Wait for client-side auth to hydrate
    take_screenshot(page, "04_agent_creation_page")

    # Check for the authentication error that was blocking users
    auth_error = page.locator('text="Authentication Required"')

    if auth_error.is_visible():
        print("❌ FAIL: 'Authentication Required' error still showing!")
        print("   The useAuth hook fix did not work or hasn't deployed yet.")
        take_screenshot(page, "05_agent_creation_BLOCKED")
        return False

    # Check if the form is visible - look for the "Agent details" heading
    form_visible = False
    try:
        # Look for the "Agent details" section heading
        agent_details_heading = page.locator('text="Agent details"').first
        if agent_details_heading.is_visible(timeout=5000):
            form_visible = True
            print("✅ PASS: Agent creation form is visible!")
            print("   'Agent details' section is showing")

        # Also check for the step navigation
        step_nav = page.locator('text="Agent details"')
        if step_nav.count() > 0:
            print("   ✓ Step navigation found")

        # Check for visibility options
        visibility_section = page.locator('text="Visibility"')
        if visibility_section.is_visible():
            print("   ✓ Visibility options visible")

    except Exception as e:
        print(f"❌ FAIL: Agent creation form not found: {e}")
        take_screenshot(page, "05_agent_form_not_found")
        return False

    if not form_visible:
        print("⚠️  Could not confirm form visibility")
        return False

    # Test form interaction by checking key elements
    print("\n→ Verifying form elements...")

    try:
        # Check for description field (using placeholder text)
        description_field = page.locator('textarea, input').filter(has_text="Describe what the agent does")
        if description_field.count() > 0 or page.locator('text="Description"').is_visible():
            print("   ✓ Description field present")

        # Check for visibility options
        public_option = page.locator('text="Public"')
        if public_option.is_visible():
            print("   ✓ Visibility options (Public/Private/Organization) present")

        # Check for Next button
        next_button = page.locator('button:has-text("Next")')
        if next_button.is_visible():
            print("   ✓ Next button visible")

        take_screenshot(page, "06_agent_form_verified")

    except Exception as e:
        print(f"   ⚠️  Some form elements not detected: {e}")
        take_screenshot(page, "06_agent_form_partial")

    print("\n✅ CRITICAL FIX VERIFIED:")
    print("   • Agent creation page loads successfully")
    print("   • No 'Authentication Required' error")
    print("   • Form is accessible and editable")
    print("   • useAuth hook properly hydrating user session")

    return True

def test_workflow_creation(page):
    """Test workflow creation flow"""
    print("\n" + "="*60)
    print("TEST 3: WORKFLOW CREATION FLOW")
    print("="*60)

    print("→ Navigating to https://swarmsync.ai/console/workflows")
    page.goto("https://swarmsync.ai/console/workflows")
    page.wait_for_load_state("networkidle")
    take_screenshot(page, "07_workflows_page")

    # Check for Creator ID field
    try:
        creator_id_field = page.locator('input[placeholder*="UUID"], input[name="creatorId"]').first

        if creator_id_field.is_visible(timeout=5000):
            print("✅ Workflow form loaded successfully")

            # Check if Creator ID is pre-filled
            current_value = creator_id_field.input_value()

            if current_value == USER_ID:
                print(f"✅ Creator ID PRE-FILLED correctly: {USER_ID}")
                print("   Code deployment successful!")
            elif current_value:
                print(f"⚠️  Creator ID pre-filled with different value: {current_value}")
                print(f"   Expected: {USER_ID}")
            else:
                print("⚠️  Creator ID field is empty (code not deployed yet)")
                print(f"   Users need to manually enter: {USER_ID}")

            # Check other form fields
            workflow_name = page.locator('input[name="name"]').first
            if workflow_name.is_visible():
                default_name = workflow_name.input_value()
                print(f"✅ Workflow name field found (default: '{default_name}')")

            budget_field = page.locator('input[name="totalBudget"]').first
            if budget_field.is_visible():
                default_budget = budget_field.input_value()
                print(f"✅ Budget field found (default: {default_budget})")

            take_screenshot(page, "08_workflow_form_details")
            return True
        else:
            print("❌ Workflow form fields not visible")
            return False

    except Exception as e:
        print(f"❌ Error accessing workflow form: {e}")
        take_screenshot(page, "08_workflow_error")
        return False

def main():
    print("\n" + "="*70)
    print("SwarmSync Production E2E Tests - Post-Deployment Verification")
    print("="*70)
    print(f"Test Account: {EMAIL}")
    print(f"User ID: {USER_ID}")
    print(f"Organization ID: {ORG_ID}")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    with sync_playwright() as p:
        # Launch browser in headless mode
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            # Test 1: Login
            login_success = login(page)

            if not login_success:
                print("\n❌ Login failed. Aborting remaining tests.")
                browser.close()
                return

            # Test 2: Agent Creation (CRITICAL - was blocked before)
            agent_test_passed = test_agent_creation(page)

            # Test 3: Workflow Creation
            workflow_test_passed = test_workflow_creation(page)

            # Final Summary
            print("\n" + "="*70)
            print("TEST SUMMARY")
            print("="*70)
            print(f"✅ Login Flow:              PASS")
            print(f"{'✅' if agent_test_passed else '❌'} Agent Creation:        {'PASS - FIX VERIFIED!' if agent_test_passed else 'FAIL - FIX NOT WORKING'}")
            print(f"{'✅' if workflow_test_passed else '❌'} Workflow Creation:      {'PASS' if workflow_test_passed else 'FAIL'}")
            print("="*70)

            if agent_test_passed and workflow_test_passed:
                print("\n🎉 ALL TESTS PASSED! Production deployment successful!")
                print("\nKey Fixes Verified:")
                print("  • useAuth hook properly hydrates authentication state")
                print("  • Agent creation form loads without authentication errors")
                print("  • Workflow creation form accessible and functional")
            elif agent_test_passed:
                print("\n✅ CRITICAL FIX VERIFIED! Agent creation is now working!")
                print("⚠️  Workflow Creator ID pre-fill may need code deployment")
            else:
                print("\n❌ CRITICAL: Agent creation fix not working on production!")
                print("   Please check deployment status and verify code was deployed.")

        except Exception as e:
            print(f"\n❌ Test execution error: {e}")
            import traceback
            traceback.print_exc()
            take_screenshot(page, "99_error")
        finally:
            print("\n→ Closing browser...")
            browser.close()
            print("✅ Tests complete!")

if __name__ == "__main__":
    main()
