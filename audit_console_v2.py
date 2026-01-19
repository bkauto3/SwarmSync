"""
SwarmSync Console & Login Audit Script v2
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
    print("SwarmSync Console Audit v2")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    results = {
        "timestamp": datetime.now().isoformat(),
        "login": {},
        "console_pages": [],
        "agent_creation": {},
        "marketplace": {},
        "billing": {},
        "wallet": {},
        "issues": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        )
        page = context.new_page()

        # Test login with correct credentials
        print("\n=== LOGIN TEST ===")
        page.goto("https://swarmsync.ai/login", wait_until="networkidle")
        page.wait_for_timeout(2000)

        # Try with username (might be email field)
        email_input = page.locator("input[type='email'], input[name='email'], input[placeholder*='email' i]").first
        password_input = page.locator("input[type='password']").first

        if email_input.is_visible() and password_input.is_visible():
            # Try username as email first
            email_input.fill("rainking6693")
            password_input.fill("chartres6693!")
            save_screenshot(page, "v2_01_login_filled")

            submit_btn = page.locator("button[type='submit'], button:has-text('Sign')").first
            submit_btn.click()
            page.wait_for_timeout(5000)
            save_screenshot(page, "v2_02_after_login")

            current_url = page.url
            print(f"After login URL: {current_url}")

            # Check if still on login page (might need @gmail.com)
            if "/login" in current_url:
                print("Trying with @gmail.com...")
                page.goto("https://swarmsync.ai/login", wait_until="networkidle")
                page.wait_for_timeout(1000)

                email_input = page.locator("input[type='email'], input[name='email']").first
                password_input = page.locator("input[type='password']").first

                email_input.fill("rainking6693@gmail.com")
                password_input.fill("chartres6693!")

                submit_btn = page.locator("button[type='submit'], button:has-text('Sign')").first
                submit_btn.click()
                page.wait_for_timeout(5000)
                save_screenshot(page, "v2_03_after_login_email")

                current_url = page.url
                print(f"After login with email URL: {current_url}")

            # Check login success
            if "/login" not in current_url:
                results["login"]["success"] = True
                results["login"]["redirect_url"] = current_url
                print("LOGIN SUCCESSFUL!")
            else:
                # Check for error
                error_elem = page.locator("[class*='error'], [class*='alert'], [role='alert']").first
                if error_elem.is_visible():
                    results["login"]["error"] = error_elem.inner_text()
                    print(f"Login error: {error_elem.inner_text()}")
                else:
                    results["login"]["success"] = False

        # If logged in, test console pages
        if results["login"].get("success"):
            print("\n=== CONSOLE PAGES TEST ===")

            console_pages = [
                ("/console", "Console Home"),
                ("/console/overview", "Overview"),
                ("/dashboard", "Dashboard"),
                ("/agents", "Agents List"),
                ("/agents/new", "Create Agent"),
                ("/console/workflows", "Workflows"),
                ("/console/billing", "Billing"),
                ("/console/wallet", "Wallet"),
                ("/console/settings", "Settings"),
            ]

            for path, name in console_pages:
                try:
                    url = f"https://swarmsync.ai{path}"
                    response = page.goto(url, wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(2000)

                    status = response.status if response else "No response"
                    page_title = page.title()
                    final_url = page.url

                    result = {
                        "name": name,
                        "path": path,
                        "status": status,
                        "title": page_title,
                        "final_url": final_url,
                        "loaded": status in [200, 304]
                    }

                    # Check for 404
                    page_content = page.content().lower()
                    if "404" in page_content or "not found" in page_content:
                        result["is_404"] = True
                        result["loaded"] = False

                    results["console_pages"].append(result)
                    status_str = "OK" if result["loaded"] and not result.get("is_404") else "FAIL"
                    print(f"{name}: {status} - {status_str}")

                    # Screenshot each page
                    safe_name = name.lower().replace(' ', '_').replace('/', '_')
                    save_screenshot(page, f"v2_console_{safe_name}")

                except Exception as e:
                    results["console_pages"].append({
                        "name": name,
                        "path": path,
                        "error": str(e)
                    })
                    print(f"{name}: ERROR - {e}")

            # Test agent creation form in detail
            print("\n=== AGENT CREATION TEST ===")
            page.goto("https://swarmsync.ai/agents/new", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v2_agent_creation_full")

            # Check for form elements
            form_elements = {
                "name_input": page.locator("input[name*='name' i], input[placeholder*='name' i]").first,
                "description": page.locator("textarea[name*='desc' i], textarea[placeholder*='desc' i]").first,
                "schema_input": page.locator("[name*='schema' i], textarea").all(),
                "submit_btn": page.locator("button[type='submit'], button:has-text('Create'), button:has-text('Save')").first
            }

            results["agent_creation"]["form_found"] = True
            results["agent_creation"]["elements"] = {}

            for elem_name, elem in form_elements.items():
                if elem_name == "schema_input":
                    results["agent_creation"]["elements"][elem_name] = len(elem)
                else:
                    try:
                        results["agent_creation"]["elements"][elem_name] = elem.is_visible() if elem else False
                    except:
                        results["agent_creation"]["elements"][elem_name] = False

            print(f"Agent creation elements: {results['agent_creation']['elements']}")

            # Test billing page
            print("\n=== BILLING PAGE TEST ===")
            page.goto("https://swarmsync.ai/console/billing", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v2_billing_page")

            # Check for pricing/plan elements
            plan_cards = page.locator("[class*='plan'], [class*='tier'], [class*='pricing']").all()
            results["billing"]["plan_cards_found"] = len(plan_cards)
            print(f"Billing plan cards: {len(plan_cards)}")

            # Test wallet page
            print("\n=== WALLET PAGE TEST ===")
            page.goto("https://swarmsync.ai/console/wallet", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v2_wallet_page")

            # Check for balance display
            balance_elem = page.locator("[class*='balance'], [class*='credit']").all()
            results["wallet"]["balance_elements"] = len(balance_elem)
            print(f"Wallet balance elements: {len(balance_elem)}")

            # Test A2A demo while logged in
            print("\n=== A2A DEMO (LOGGED IN) ===")
            page.goto("https://swarmsync.ai/demo/a2a", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v2_a2a_logged_in")

            # Click run demo
            run_btn = page.locator("button:has-text('Run'), button:has-text('Demo')").first
            if run_btn.is_visible():
                run_btn.click()
                page.wait_for_timeout(8000)  # Wait for demo to run
                save_screenshot(page, "v2_a2a_running")
                print("A2A Demo executed")

            # Test workflow demo while logged in
            print("\n=== WORKFLOW DEMO (LOGGED IN) ===")
            page.goto("https://swarmsync.ai/demo/workflows", wait_until="networkidle")
            page.wait_for_timeout(2000)
            save_screenshot(page, "v2_workflow_logged_in")

            # Check if run button is now enabled
            run_workflow_btn = page.locator("button:has-text('Run'), button:has-text('Execute')").first
            if run_workflow_btn.is_visible():
                is_disabled = run_workflow_btn.is_disabled()
                results["workflow_run_enabled"] = not is_disabled
                print(f"Workflow run button enabled: {not is_disabled}")

        browser.close()

    # Save results
    results_path = f"{SCREENSHOTS_DIR}/console_audit_v2_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_path}")

    print("\n" + "=" * 60)
    print("CONSOLE AUDIT v2 COMPLETE")
    print("=" * 60)

    return results

if __name__ == "__main__":
    main()
