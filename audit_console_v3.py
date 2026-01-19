"""
SwarmSync Console & Login Audit Script v3
Tests logged-in functionality with correct credentials
"""
from playwright.sync_api import sync_playwright
import json
import os
from datetime import datetime

SCREENSHOTS_DIR = "C:/Users/Ben/Desktop/Github/Agent-Market/audit_screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def save_screenshot(page, name):
    path = f"{SCREENSHOTS_DIR}/{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"Screenshot: {path}")
    return path

def main():
    print("=" * 60)
    print("SwarmSync Console Audit v3")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    results = {
        "timestamp": datetime.now().isoformat(),
        "login": {},
        "console_pages": [],
        "agent_creation": {},
        "billing": {},
        "wallet": {},
        "workflows": {},
        "a2a_demo": {},
        "issues": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        )
        page = context.new_page()

        # Login with correct credentials
        print("\n=== LOGIN TEST ===")
        page.goto("https://swarmsync.ai/login", wait_until="networkidle")
        page.wait_for_timeout(2000)

        email_input = page.locator("input[type='email'], input[name='email']").first
        password_input = page.locator("input[type='password']").first

        email_input.fill("rainking6693@gmail.com")
        password_input.fill("Hudson1234%")
        save_screenshot(page, "v3_01_login_filled")

        submit_btn = page.locator("button[type='submit'], button:has-text('Sign In')").first
        submit_btn.click()
        page.wait_for_timeout(5000)
        save_screenshot(page, "v3_02_after_login")

        current_url = page.url
        print(f"After login URL: {current_url}")

        # Check login success
        if "/login" not in current_url:
            results["login"]["success"] = True
            results["login"]["redirect_url"] = current_url
            print("LOGIN SUCCESSFUL!")
        else:
            error_elem = page.locator("[class*='error'], [class*='alert']").first
            if error_elem.is_visible():
                error_text = error_elem.inner_text()
                results["login"]["error"] = error_text
                print(f"Login error: {error_text}")
            results["login"]["success"] = False

        # If logged in, test all console features
        if results["login"].get("success"):
            print("\n=== CONSOLE OVERVIEW ===")
            page.goto("https://swarmsync.ai/console/overview", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v3_console_overview")

            # Check for sidebar
            sidebar = page.locator("aside, nav[class*='sidebar'], [class*='sidebar']").first
            results["console_overview"] = {
                "sidebar_visible": sidebar.is_visible() if sidebar else False,
                "url": page.url
            }
            print(f"Console overview loaded: {page.url}")

            print("\n=== DASHBOARD ===")
            page.goto("https://swarmsync.ai/dashboard", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v3_dashboard")
            print(f"Dashboard URL: {page.url}")

            print("\n=== AGENTS LIST ===")
            page.goto("https://swarmsync.ai/agents", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v3_agents_list")

            agent_cards = page.locator("[class*='card'], [class*='agent']").all()
            print(f"Agent cards found: {len(agent_cards)}")

            print("\n=== CREATE AGENT ===")
            page.goto("https://swarmsync.ai/agents/new", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v3_agent_create")

            # Check form elements
            form = page.locator("form").first
            if form and form.is_visible():
                results["agent_creation"]["form_found"] = True

                # Check for onboarding banner
                banner = page.locator("[class*='banner'], [class*='onboarding'], [class*='guide']").first
                results["agent_creation"]["onboarding_banner"] = banner.is_visible() if banner else False

                # Check input fields
                inputs = page.locator("input, textarea, select").all()
                results["agent_creation"]["input_count"] = len(inputs)
                print(f"Agent creation form found with {len(inputs)} inputs")
            else:
                results["agent_creation"]["form_found"] = False
                # Check for access denied message
                page_text = page.content().lower()
                if "access" in page_text or "permission" in page_text:
                    results["agent_creation"]["access_denied"] = True
                    print("Agent creation: Access restricted")

            print("\n=== WORKFLOWS ===")
            page.goto("https://swarmsync.ai/console/workflows", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v3_workflows")
            results["workflows"]["url"] = page.url
            print(f"Workflows URL: {page.url}")

            print("\n=== BILLING ===")
            page.goto("https://swarmsync.ai/console/billing", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v3_billing")

            # Check for plan/pricing elements
            plan_elements = page.locator("[class*='plan'], [class*='tier'], [class*='subscription']").all()
            stripe_links = page.locator("a[href*='stripe'], button[class*='stripe']").all()
            results["billing"]["plan_elements"] = len(plan_elements)
            results["billing"]["stripe_links"] = len(stripe_links)
            print(f"Billing: {len(plan_elements)} plan elements, {len(stripe_links)} stripe links")

            print("\n=== WALLET ===")
            page.goto("https://swarmsync.ai/console/wallet", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v3_wallet")

            balance = page.locator("[class*='balance'], [class*='credit'], [class*='amount']").all()
            transactions = page.locator("[class*='transaction'], [class*='history'], table tr").all()
            results["wallet"]["balance_elements"] = len(balance)
            results["wallet"]["transaction_rows"] = len(transactions)
            print(f"Wallet: {len(balance)} balance elements, {len(transactions)} transaction rows")

            print("\n=== SETTINGS ===")
            page.goto("https://swarmsync.ai/console/settings", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v3_settings")

            api_keys = page.locator("[class*='api'], [class*='key'], input[type='password']").all()
            results["settings"] = {"api_key_elements": len(api_keys)}
            print(f"Settings: {len(api_keys)} API key related elements")

            print("\n=== A2A DEMO (LOGGED IN) ===")
            page.goto("https://swarmsync.ai/demo/a2a", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v3_a2a_demo")

            # Try running the demo
            run_btn = page.locator("button:has-text('Run Live Demo')").first
            if run_btn and run_btn.is_visible():
                print("Clicking Run Live Demo...")
                run_btn.click()
                page.wait_for_timeout(10000)  # Wait for demo execution
                save_screenshot(page, "v3_a2a_demo_running")

                # Check for timeline/log updates
                timeline = page.locator("[class*='timeline'], [class*='step'], [class*='log']").all()
                results["a2a_demo"]["timeline_elements"] = len(timeline)
                print(f"A2A Demo: {len(timeline)} timeline elements after run")

            print("\n=== WORKFLOW DEMO (LOGGED IN) ===")
            page.goto("https://swarmsync.ai/demo/workflows", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v3_workflow_demo")

            # Check if run workflow is enabled for logged-in user
            run_workflow = page.locator("button:has-text('Run'), button:has-text('Execute')").first
            if run_workflow:
                is_disabled = run_workflow.is_disabled()
                results["workflow_demo"] = {"run_enabled": not is_disabled}
                print(f"Workflow run button enabled: {not is_disabled}")

            # Test individual agent page
            print("\n=== AGENT DETAIL PAGE ===")
            # Click on first agent in marketplace
            page.goto("https://swarmsync.ai/agents", wait_until="networkidle")
            page.wait_for_timeout(2000)

            first_agent = page.locator("a[href*='/agents/']").first
            if first_agent and first_agent.is_visible():
                first_agent.click()
                page.wait_for_timeout(3000)
                save_screenshot(page, "v3_agent_detail")

                # Check for quality testing section
                quality_section = page.locator("[class*='quality'], [class*='testing'], [class*='benchmark']").all()
                results["agent_detail"] = {
                    "url": page.url,
                    "quality_elements": len(quality_section)
                }
                print(f"Agent detail page: {page.url}")

        browser.close()

    # Save results
    results_path = f"{SCREENSHOTS_DIR}/console_audit_v3_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_path}")

    print("\n" + "=" * 60)
    print("CONSOLE AUDIT v3 COMPLETE")
    print("=" * 60)

    return results

if __name__ == "__main__":
    main()
