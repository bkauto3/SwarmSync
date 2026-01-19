"""
SwarmSync API Audit Script
Tests API endpoints
"""
from playwright.sync_api import sync_playwright
import json
import os
from datetime import datetime

SCREENSHOTS_DIR = "C:/Users/Ben/Desktop/Github/Agent-Market/audit_screenshots"

def main():
    print("=" * 60)
    print("SwarmSync API Audit")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    results = {
        "timestamp": datetime.now().isoformat(),
        "endpoints": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Test API endpoints
        endpoints = [
            ("/api/demo", "Demo API"),
            ("/api/marketplace", "Marketplace API"),
            ("/api/agents", "Agents API"),
            ("/api/health", "Health Check"),
        ]

        for path, name in endpoints:
            try:
                url = f"https://swarmsync.ai{path}"
                response = page.goto(url, wait_until="networkidle", timeout=30000)
                status = response.status if response else "No response"

                # Try to get response body
                try:
                    content = page.content()
                    # Check if it's JSON
                    if "application/json" in (response.headers.get("content-type", "") if response else ""):
                        body_preview = content[:500]
                    else:
                        body_preview = content[:200]
                except:
                    body_preview = "Could not read body"

                results["endpoints"].append({
                    "name": name,
                    "path": path,
                    "status": status,
                    "success": status in [200, 201, 304]
                })

                status_str = "OK" if status in [200, 201, 304] else "FAIL"
                print(f"{name} ({path}): {status} - {status_str}")

            except Exception as e:
                results["endpoints"].append({
                    "name": name,
                    "path": path,
                    "error": str(e)
                })
                print(f"{name} ({path}): ERROR - {e}")

        # Test specific pages for forms
        print("\n=== FORM SUBMISSION TESTS ===")

        # Test provider application page
        page.goto("https://swarmsync.ai/providers", wait_until="networkidle")
        page.wait_for_timeout(2000)

        # Check for application form
        form = page.locator("form").first
        if form.is_visible():
            print("Provider application form: FOUND")
            results["provider_form"] = True
        else:
            print("Provider application form: NOT FOUND")
            results["provider_form"] = False

        # Take screenshot
        page.screenshot(path=f"{SCREENSHOTS_DIR}/api_providers_page.png", full_page=True)

        # Test pricing contact form
        page.goto("https://swarmsync.ai/pricing", wait_until="networkidle")
        page.wait_for_timeout(2000)

        # Scroll to bottom for enterprise form
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1000)

        enterprise_form = page.locator("form").first
        if enterprise_form.is_visible():
            print("Enterprise contact form: FOUND")
            results["enterprise_form"] = True

            # Check form fields
            name_input = page.locator("input[name*='name' i], input[placeholder*='name' i]").first
            email_input = page.locator("input[name*='email' i], input[type='email']").first
            message_input = page.locator("textarea").first
            submit_btn = page.locator("button[type='submit'], button:has-text('Submit')").first

            results["enterprise_form_fields"] = {
                "name": name_input.is_visible() if name_input else False,
                "email": email_input.is_visible() if email_input else False,
                "message": message_input.is_visible() if message_input else False,
                "submit": submit_btn.is_visible() if submit_btn else False
            }
            print(f"Form fields: {results['enterprise_form_fields']}")
        else:
            print("Enterprise contact form: NOT FOUND")
            results["enterprise_form"] = False

        browser.close()

    # Save results
    results_path = f"{SCREENSHOTS_DIR}/api_audit_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_path}")

    print("\n" + "=" * 60)
    print("API AUDIT COMPLETE")
    print("=" * 60)

    return results

if __name__ == "__main__":
    main()
