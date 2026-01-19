"""
SwarmSync Website Audit Script
Comprehensive audit of https://swarmsync.ai/
"""
from playwright.sync_api import sync_playwright
import json
import os
from datetime import datetime

# Create screenshots directory
SCREENSHOTS_DIR = "C:/Users/Ben/Desktop/Github/Agent-Market/audit_screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def save_screenshot(page, name):
    """Save screenshot with timestamp"""
    path = f"{SCREENSHOTS_DIR}/{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"Screenshot saved: {path}")
    return path

def audit_homepage(page):
    """Audit the homepage"""
    print("\n=== HOMEPAGE AUDIT ===")
    page.goto("https://swarmsync.ai/", wait_until="networkidle")
    page.wait_for_timeout(2000)

    results = {
        "url": page.url,
        "title": page.title(),
        "logo_found": False,
        "navbar_links": [],
        "footer_links": [],
        "cta_buttons": [],
        "issues": []
    }

    # Check logo
    try:
        logo = page.locator("img[alt*='logo' i], img[src*='logo' i], .logo, [class*='logo']").first
        if logo.is_visible():
            results["logo_found"] = True
            logo_src = logo.get_attribute("src")
            print(f"Logo found: {logo_src}")
        else:
            results["issues"].append("Logo not visible")
    except Exception as e:
        results["issues"].append(f"Logo check error: {str(e)}")

    # Check navbar links
    nav_links = page.locator("nav a, header a").all()
    for link in nav_links:
        try:
            text = link.inner_text().strip()
            href = link.get_attribute("href")
            if text and href:
                results["navbar_links"].append({"text": text, "href": href})
        except:
            pass
    print(f"Found {len(results['navbar_links'])} navbar links")

    # Check footer links
    footer_links = page.locator("footer a").all()
    for link in footer_links:
        try:
            text = link.inner_text().strip()
            href = link.get_attribute("href")
            if text and href:
                results["footer_links"].append({"text": text, "href": href})
        except:
            pass
    print(f"Found {len(results['footer_links'])} footer links")

    # Check CTA buttons
    cta_buttons = page.locator("button, a[class*='btn'], a[class*='button'], .cta").all()
    for btn in cta_buttons[:10]:  # Limit to first 10
        try:
            text = btn.inner_text().strip()
            if text:
                results["cta_buttons"].append(text)
        except:
            pass
    print(f"Found {len(results['cta_buttons'])} CTA buttons")

    save_screenshot(page, "01_homepage")
    return results

def audit_navigation(page):
    """Test all navigation links"""
    print("\n=== NAVIGATION AUDIT ===")
    results = {"pages_tested": [], "broken_links": []}

    # Key pages to test
    pages = [
        ("/", "Homepage"),
        ("/about", "About"),
        ("/platform", "Platform"),
        ("/pricing", "Pricing"),
        ("/resources", "Resources"),
        ("/security", "Security"),
        ("/providers", "Providers"),
        ("/use-cases", "Use Cases"),
        ("/methodology", "Methodology"),
        ("/demo/a2a", "A2A Demo"),
        ("/demo/workflows", "Workflow Demo"),
    ]

    for path, name in pages:
        try:
            url = f"https://swarmsync.ai{path}"
            response = page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1000)

            status = response.status if response else "No response"
            results["pages_tested"].append({
                "name": name,
                "path": path,
                "status": status,
                "title": page.title(),
                "loaded": status == 200 or status == 304
            })

            if status not in [200, 304]:
                results["broken_links"].append(f"{name} ({path}): {status}")

            print(f"{name}: {status}")

            # Take screenshot of key pages
            if path in ["/", "/demo/a2a", "/demo/workflows", "/pricing"]:
                save_screenshot(page, f"nav_{name.lower().replace(' ', '_')}")

        except Exception as e:
            results["broken_links"].append(f"{name} ({path}): {str(e)}")
            print(f"{name}: ERROR - {str(e)}")

    return results

def audit_demo_a2a(page):
    """Audit the A2A demo page"""
    print("\n=== A2A DEMO AUDIT ===")
    page.goto("https://swarmsync.ai/demo/a2a", wait_until="networkidle")
    page.wait_for_timeout(2000)

    results = {
        "url": page.url,
        "agents_loaded": False,
        "run_button_found": False,
        "timeline_found": False,
        "issues": []
    }

    save_screenshot(page, "02_a2a_demo_initial")

    # Check for agent cards
    agent_cards = page.locator("[class*='agent'], [class*='card']").all()
    results["agents_loaded"] = len(agent_cards) > 0
    print(f"Agent cards found: {len(agent_cards)}")

    # Check for Run Demo button
    run_buttons = page.locator("button:has-text('Run'), button:has-text('Demo'), button:has-text('Start')").all()
    results["run_button_found"] = len(run_buttons) > 0
    print(f"Run buttons found: {len(run_buttons)}")

    # Try clicking run demo if found
    if run_buttons:
        try:
            run_buttons[0].click()
            page.wait_for_timeout(3000)
            save_screenshot(page, "02_a2a_demo_running")

            # Check for timeline updates
            timeline = page.locator("[class*='timeline'], [class*='step'], [class*='log']").all()
            results["timeline_found"] = len(timeline) > 0
            print(f"Timeline/log elements found: {len(timeline)}")

            page.wait_for_timeout(5000)
            save_screenshot(page, "02_a2a_demo_complete")
        except Exception as e:
            results["issues"].append(f"Run demo error: {str(e)}")

    return results

def audit_demo_workflows(page):
    """Audit the workflows demo page"""
    print("\n=== WORKFLOW DEMO AUDIT ===")
    page.goto("https://swarmsync.ai/demo/workflows", wait_until="networkidle")
    page.wait_for_timeout(2000)

    results = {
        "url": page.url,
        "templates_found": False,
        "json_editor_found": False,
        "run_button_found": False,
        "issues": []
    }

    save_screenshot(page, "03_workflow_demo")

    # Check for workflow templates
    templates = page.locator("[class*='template'], [class*='workflow']").all()
    results["templates_found"] = len(templates) > 0
    print(f"Workflow templates found: {len(templates)}")

    # Check for JSON editor
    json_editor = page.locator("textarea, [class*='json'], [class*='editor'], pre, code").all()
    results["json_editor_found"] = len(json_editor) > 0
    print(f"JSON/editor elements found: {len(json_editor)}")

    # Check for run button
    run_buttons = page.locator("button:has-text('Run'), button:has-text('Execute')").all()
    results["run_button_found"] = len(run_buttons) > 0
    print(f"Run buttons found: {len(run_buttons)}")

    return results

def audit_login_and_console(page, email, password):
    """Login and audit console features"""
    print("\n=== LOGIN & CONSOLE AUDIT ===")

    results = {
        "login_successful": False,
        "console_pages": [],
        "issues": []
    }

    # Go to login page
    page.goto("https://swarmsync.ai/auth/signin", wait_until="networkidle")
    page.wait_for_timeout(2000)
    save_screenshot(page, "04_login_page")

    # Try to login
    try:
        # Look for email input
        email_input = page.locator("input[type='email'], input[name='email'], input[placeholder*='email' i]").first
        if email_input.is_visible():
            email_input.fill(email)
            print("Email entered")

        # Look for password input
        password_input = page.locator("input[type='password'], input[name='password']").first
        if password_input.is_visible():
            password_input.fill(password)
            print("Password entered")

        save_screenshot(page, "04_login_filled")

        # Click login button
        login_btn = page.locator("button[type='submit'], button:has-text('Sign'), button:has-text('Log')").first
        if login_btn.is_visible():
            login_btn.click()
            page.wait_for_timeout(5000)

            save_screenshot(page, "04_after_login")

            # Check if login was successful
            if "/console" in page.url or "/dashboard" in page.url or "/agents" in page.url:
                results["login_successful"] = True
                print("Login successful!")
            else:
                print(f"After login URL: {page.url}")
                # Check for error messages
                error = page.locator("[class*='error'], [class*='alert']").first
                if error.is_visible():
                    results["issues"].append(f"Login error: {error.inner_text()}")
    except Exception as e:
        results["issues"].append(f"Login error: {str(e)}")
        print(f"Login error: {str(e)}")

    # If logged in, audit console pages
    if results["login_successful"]:
        console_pages = [
            ("/console/overview", "Console Overview"),
            ("/console/agents", "Agents List"),
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
                results["console_pages"].append({
                    "name": name,
                    "path": path,
                    "status": status,
                    "loaded": status == 200 or status == 304
                })

                print(f"{name}: {status}")
                save_screenshot(page, f"05_console_{name.lower().replace(' ', '_')}")

            except Exception as e:
                results["issues"].append(f"{name}: {str(e)}")
                print(f"{name}: ERROR - {str(e)}")

    return results

def audit_create_agent(page):
    """Test agent creation flow"""
    print("\n=== AGENT CREATION AUDIT ===")

    results = {
        "form_found": False,
        "fields_found": [],
        "issues": []
    }

    page.goto("https://swarmsync.ai/agents/new", wait_until="networkidle")
    page.wait_for_timeout(2000)
    save_screenshot(page, "06_create_agent_page")

    # Check for form elements
    form = page.locator("form").first
    if form.is_visible():
        results["form_found"] = True

        # Check for common fields
        fields = [
            ("input[name*='name' i]", "Agent Name"),
            ("textarea[name*='desc' i], input[name*='desc' i]", "Description"),
            ("[name*='schema' i], [name*='input' i]", "Input Schema"),
            ("[name*='budget' i], [name*='price' i]", "Budget/Pricing"),
            ("[name*='endpoint' i], [name*='url' i]", "Endpoint/URL"),
        ]

        for selector, field_name in fields:
            field = page.locator(selector).first
            try:
                if field.is_visible():
                    results["fields_found"].append(field_name)
            except:
                pass

        print(f"Fields found: {results['fields_found']}")
    else:
        results["issues"].append("Agent creation form not found")

    return results

def audit_responsive(page):
    """Test responsive breakpoints"""
    print("\n=== RESPONSIVE AUDIT ===")

    results = {"breakpoints_tested": []}

    viewports = [
        (1920, 1080, "Desktop Large"),
        (1366, 768, "Desktop"),
        (1024, 768, "Tablet Landscape"),
        (768, 1024, "Tablet Portrait"),
        (375, 812, "Mobile iPhone X"),
        (360, 640, "Mobile Android"),
    ]

    page.goto("https://swarmsync.ai/", wait_until="networkidle")

    for width, height, name in viewports:
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(500)

        # Check for horizontal scroll (overflow)
        body_width = page.evaluate("document.body.scrollWidth")
        has_overflow = body_width > width

        results["breakpoints_tested"].append({
            "name": name,
            "width": width,
            "height": height,
            "has_overflow": has_overflow
        })

        print(f"{name} ({width}x{height}): {'OVERFLOW' if has_overflow else 'OK'}")
        save_screenshot(page, f"07_responsive_{name.lower().replace(' ', '_')}")

    return results

def main():
    """Run the full audit"""
    print("=" * 60)
    print("SwarmSync Website Audit")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    audit_results = {
        "timestamp": datetime.now().isoformat(),
        "site": "https://swarmsync.ai",
        "sections": {}
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        )
        page = context.new_page()

        # Run audits
        audit_results["sections"]["homepage"] = audit_homepage(page)
        audit_results["sections"]["navigation"] = audit_navigation(page)
        audit_results["sections"]["demo_a2a"] = audit_demo_a2a(page)
        audit_results["sections"]["demo_workflows"] = audit_demo_workflows(page)
        audit_results["sections"]["responsive"] = audit_responsive(page)

        # Login and console audit
        audit_results["sections"]["console"] = audit_login_and_console(
            page,
            "rainking6693@gmail.com",
            "Hudson123%"
        )

        # If logged in, test agent creation
        if audit_results["sections"]["console"].get("login_successful"):
            audit_results["sections"]["create_agent"] = audit_create_agent(page)

        browser.close()

    # Save results
    results_path = f"{SCREENSHOTS_DIR}/audit_results.json"
    with open(results_path, "w") as f:
        json.dump(audit_results, f, indent=2)
    print(f"\nResults saved to: {results_path}")

    print("\n" + "=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60)

    return audit_results

if __name__ == "__main__":
    main()
