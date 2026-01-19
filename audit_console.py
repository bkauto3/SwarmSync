"""
SwarmSync Console & Login Audit Script
Tests logged-in functionality
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
    print("SwarmSync Console Audit")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    results = {
        "timestamp": datetime.now().isoformat(),
        "login": {},
        "console_pages": [],
        "agent_creation": {},
        "marketplace": {},
        "issues": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        )
        page = context.new_page()

        # Test login page at /login
        print("\n=== LOGIN TEST ===")
        page.goto("https://swarmsync.ai/login", wait_until="networkidle")
        page.wait_for_timeout(2000)
        save_screenshot(page, "console_01_login_page")

        login_url = page.url
        login_title = page.title()
        print(f"Login URL: {login_url}")
        print(f"Login Title: {login_title}")

        # Check if we have a login form or OAuth buttons
        email_inputs = page.locator("input[type='email'], input[name='email'], input[placeholder*='email' i], input[id*='email' i]").all()
        password_inputs = page.locator("input[type='password']").all()
        oauth_buttons = page.locator("button:has-text('Google'), button:has-text('GitHub'), button:has-text('Continue with'), a:has-text('Google'), a:has-text('GitHub')").all()

        print(f"Email inputs found: {len(email_inputs)}")
        print(f"Password inputs found: {len(password_inputs)}")
        print(f"OAuth buttons found: {len(oauth_buttons)}")

        results["login"]["has_email_input"] = len(email_inputs) > 0
        results["login"]["has_password_input"] = len(password_inputs) > 0
        results["login"]["has_oauth"] = len(oauth_buttons) > 0

        # Try to login
        if email_inputs and password_inputs:
            try:
                email_inputs[0].fill("rainking6693@gmail.com")
                password_inputs[0].fill("Hudson123%")
                save_screenshot(page, "console_02_login_filled")

                # Find and click submit button
                submit_btn = page.locator("button[type='submit'], button:has-text('Sign'), button:has-text('Log in'), button:has-text('Continue')").first
                if submit_btn.is_visible():
                    submit_btn.click()
                    page.wait_for_timeout(5000)
                    save_screenshot(page, "console_03_after_login")

                    current_url = page.url
                    print(f"After login URL: {current_url}")

                    # Check for success indicators
                    if any(x in current_url for x in ["/console", "/dashboard", "/agents", "/overview"]):
                        results["login"]["success"] = True
                        print("LOGIN SUCCESSFUL!")
                    elif "/login" in current_url or "/signin" in current_url:
                        # Check for error messages
                        error_elem = page.locator("[class*='error'], [class*='alert'], [role='alert']").first
                        if error_elem.is_visible():
                            error_text = error_elem.inner_text()
                            results["login"]["error"] = error_text
                            print(f"Login error: {error_text}")
                        else:
                            results["login"]["success"] = False
                            results["login"]["note"] = "Still on login page, no error shown"
                    else:
                        results["login"]["success"] = True
                        results["login"]["redirect_url"] = current_url
                        print(f"Redirected to: {current_url}")
            except Exception as e:
                results["login"]["error"] = str(e)
                print(f"Login error: {e}")
        else:
            # Maybe OAuth only - check for magic link option
            magic_link = page.locator("button:has-text('magic'), button:has-text('email link'), a:has-text('magic')").first
            if magic_link.is_visible():
                results["login"]["type"] = "magic_link"
                print("Login uses magic link / passwordless")
            elif oauth_buttons:
                results["login"]["type"] = "oauth_only"
                print("Login uses OAuth only (Google/GitHub)")

        # Test console pages if we're logged in
        if results["login"].get("success"):
            print("\n=== CONSOLE PAGES TEST ===")
            console_pages = [
                ("/console/overview", "Overview"),
                ("/console", "Console Home"),
                ("/agents", "Agents List"),
                ("/agents/new", "Create Agent"),
                ("/console/workflows", "Workflows"),
                ("/console/billing", "Billing"),
                ("/console/wallet", "Wallet"),
                ("/console/settings", "Settings"),
                ("/dashboard", "Dashboard"),
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

                    # Check for 404 or error pages
                    if "404" in page.content() or "not found" in page.content().lower():
                        result["is_404"] = True
                        result["loaded"] = False

                    results["console_pages"].append(result)
                    status_str = "OK" if result["loaded"] and not result.get("is_404") else "FAIL"
                    print(f"{name}: {status} - {status_str}")

                    # Screenshot key pages
                    safe_name = name.lower().replace(' ', '_').replace('/', '_')
                    save_screenshot(page, f"console_{safe_name}")

                except Exception as e:
                    results["console_pages"].append({
                        "name": name,
                        "path": path,
                        "error": str(e)
                    })
                    print(f"{name}: ERROR - {e}")

            # Test agent creation form
            print("\n=== AGENT CREATION TEST ===")
            page.goto("https://swarmsync.ai/agents/new", wait_until="networkidle")
            page.wait_for_timeout(2000)

            form = page.locator("form").first
            if form.is_visible():
                results["agent_creation"]["form_found"] = True

                # Find all input fields
                inputs = page.locator("input, textarea, select").all()
                for inp in inputs:
                    try:
                        name = inp.get_attribute("name") or inp.get_attribute("id") or inp.get_attribute("placeholder")
                        if name:
                            results["agent_creation"].setdefault("fields", []).append(name)
                    except:
                        pass

                print(f"Agent form fields: {results['agent_creation'].get('fields', [])}")
            else:
                results["agent_creation"]["form_found"] = False
                # Check if access denied
                page_content = page.content().lower()
                if "access" in page_content or "permission" in page_content or "denied" in page_content:
                    results["agent_creation"]["access_denied"] = True
                    print("Agent creation: Access denied")

            save_screenshot(page, "console_agent_creation")

        # Test marketplace / agents list
        print("\n=== MARKETPLACE TEST ===")
        page.goto("https://swarmsync.ai/agents", wait_until="networkidle")
        page.wait_for_timeout(2000)
        save_screenshot(page, "console_marketplace")

        agent_cards = page.locator("[class*='card'], [class*='agent'], article").all()
        results["marketplace"]["agent_cards_found"] = len(agent_cards)
        print(f"Marketplace: {len(agent_cards)} agent cards found")

        # Check for quality badges, test pass rate, etc.
        badges = page.locator("[class*='badge'], [class*='certified'], [class*='verified']").all()
        results["marketplace"]["badges_found"] = len(badges)
        print(f"Quality badges found: {len(badges)}")

        browser.close()

    # Save results
    results_path = f"{SCREENSHOTS_DIR}/console_audit_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_path}")

    print("\n" + "=" * 60)
    print("CONSOLE AUDIT COMPLETE")
    print("=" * 60)

    return results

if __name__ == "__main__":
    main()
