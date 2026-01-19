"""
SwarmSync - Test Agent and Workflow Creation Flows
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
    print("SwarmSync - Create Agent & Workflow Test")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    results = {
        "timestamp": datetime.now().isoformat(),
        "agent_creation": {},
        "workflow_creation": {}
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        )
        page = context.new_page()

        # Login first
        print("\n=== LOGIN ===")
        page.goto("https://swarmsync.ai/login", wait_until="networkidle")
        page.wait_for_timeout(2000)

        email_input = page.locator("input[type='email']").first
        password_input = page.locator("input[type='password']").first
        email_input.fill("rainking6693@gmail.com")
        password_input.fill("Hudson1234%")

        submit_btn = page.locator("button[type='submit']").first
        submit_btn.click()
        page.wait_for_timeout(5000)

        if "/console" in page.url or "/overview" in page.url:
            print("Login successful!")
        else:
            print(f"Login may have failed. URL: {page.url}")

        # ============================================
        # TEST 1: TRY TO CREATE AN AGENT
        # ============================================
        print("\n=== TEST AGENT CREATION ===")

        # Try via the console "+ Create Agent" button
        page.goto("https://swarmsync.ai/console/overview", wait_until="networkidle")
        page.wait_for_timeout(2000)

        create_agent_btn = page.locator("button:has-text('Create Agent'), a:has-text('Create Agent')").first
        if create_agent_btn and create_agent_btn.is_visible():
            print("Found 'Create Agent' button, clicking...")
            create_agent_btn.click()
            page.wait_for_timeout(3000)
            save_screenshot(page, "create_01_after_create_agent_click")
            print(f"After clicking Create Agent, URL: {page.url}")
            results["agent_creation"]["via_button_url"] = page.url

        # Try direct navigation to /agents/new
        page.goto("https://swarmsync.ai/agents/new", wait_until="networkidle")
        page.wait_for_timeout(2000)
        save_screenshot(page, "create_02_agents_new_page")

        # Check what's on the page
        page_content = page.content()
        if "Sign in to deploy" in page_content:
            results["agent_creation"]["status"] = "BLOCKED - requires provider role"
            print("Agent creation BLOCKED - requires provider role")

            # Check if there's a way to request provider access
            provider_link = page.locator("a:has-text('provider'), a:has-text('apply'), button:has-text('request')").first
            if provider_link and provider_link.is_visible():
                results["agent_creation"]["has_provider_link"] = True
        else:
            results["agent_creation"]["status"] = "FORM AVAILABLE"
            print("Agent creation form is available!")

            # Try to fill out the form
            form = page.locator("form").first
            if form and form.is_visible():
                # Look for form fields
                name_input = page.locator("input[name*='name' i], input[placeholder*='name' i]").first
                desc_input = page.locator("textarea[name*='desc' i], textarea[placeholder*='desc' i], textarea").first

                if name_input and name_input.is_visible():
                    name_input.fill("Test Audit Agent")
                    print("Filled agent name")

                if desc_input and desc_input.is_visible():
                    desc_input.fill("This is a test agent created during the audit process.")
                    print("Filled agent description")

                save_screenshot(page, "create_03_agent_form_filled")

                # Try to submit
                submit_btn = page.locator("button[type='submit'], button:has-text('Create'), button:has-text('Save')").first
                if submit_btn and submit_btn.is_visible():
                    print("Found submit button, clicking...")
                    submit_btn.click()
                    page.wait_for_timeout(5000)
                    save_screenshot(page, "create_04_agent_after_submit")
                    results["agent_creation"]["submitted"] = True
                    results["agent_creation"]["result_url"] = page.url
                    print(f"After submit, URL: {page.url}")

        # ============================================
        # TEST 2: CREATE A WORKFLOW
        # ============================================
        print("\n=== TEST WORKFLOW CREATION ===")

        page.goto("https://swarmsync.ai/console/workflows", wait_until="networkidle")
        page.wait_for_timeout(2000)
        save_screenshot(page, "create_05_workflows_page")

        # Check if we have the workflow creation form
        workflow_form = page.locator("form").first
        if workflow_form and workflow_form.is_visible():
            results["workflow_creation"]["form_found"] = True
            print("Workflow creation form found!")

            # Fill out workflow details
            # Workflow name
            name_input = page.locator("input[placeholder*='name' i], input[name*='name' i]").first
            if name_input and name_input.is_visible():
                name_input.fill("Audit Test Workflow")
                print("Filled workflow name")

            # Description
            desc_input = page.locator("textarea[placeholder*='desc' i], textarea[name*='desc' i], textarea").first
            if desc_input and desc_input.is_visible():
                desc_input.fill("Test workflow created during audit")
                print("Filled workflow description")

            # Budget
            budget_input = page.locator("input[name*='budget' i], input[placeholder*='budget' i], input[type='number']").first
            if budget_input and budget_input.is_visible():
                budget_input.fill("25")
                print("Filled budget")

            save_screenshot(page, "create_06_workflow_form_filled")

            # Try to add a step
            add_step_btn = page.locator("button:has-text('Add Step'), button:has-text('+ Add')").first
            if add_step_btn and add_step_btn.is_visible():
                print("Found 'Add Step' button, clicking...")
                add_step_btn.click()
                page.wait_for_timeout(2000)
                save_screenshot(page, "create_07_workflow_add_step")
                results["workflow_creation"]["add_step_clicked"] = True

                # Check if a modal or new section appeared
                step_modal = page.locator("[class*='modal'], [class*='dialog'], [class*='step-form']").first
                if step_modal and step_modal.is_visible():
                    results["workflow_creation"]["step_modal_appeared"] = True
                    print("Step modal/form appeared!")
                    save_screenshot(page, "create_08_workflow_step_modal")

            # Try to create the workflow
            create_btn = page.locator("button:has-text('Create Workflow'), button[type='submit']").first
            if create_btn and create_btn.is_visible():
                print("Found 'Create Workflow' button, clicking...")
                create_btn.click()
                page.wait_for_timeout(5000)
                save_screenshot(page, "create_09_workflow_after_submit")
                results["workflow_creation"]["submitted"] = True
                results["workflow_creation"]["result_url"] = page.url

                # Check for success/error messages
                success_msg = page.locator("[class*='success'], [class*='toast']").first
                error_msg = page.locator("[class*='error'], [class*='alert']").first

                if success_msg and success_msg.is_visible():
                    results["workflow_creation"]["success"] = True
                    results["workflow_creation"]["message"] = success_msg.inner_text()
                    print(f"Success: {success_msg.inner_text()}")
                elif error_msg and error_msg.is_visible():
                    results["workflow_creation"]["error"] = error_msg.inner_text()
                    print(f"Error: {error_msg.inner_text()}")

                print(f"After submit, URL: {page.url}")
        else:
            results["workflow_creation"]["form_found"] = False
            print("No workflow creation form found")

        # ============================================
        # TEST 3: RUN A WORKFLOW (if any exist)
        # ============================================
        print("\n=== TEST RUNNING A WORKFLOW ===")

        # Check "Existing Workflows" section
        existing_workflows = page.locator("[class*='workflow'], [class*='list'] [class*='item']").all()
        results["existing_workflows_count"] = len(existing_workflows)
        print(f"Found {len(existing_workflows)} existing workflows")

        if existing_workflows:
            # Try to click on one
            existing_workflows[0].click()
            page.wait_for_timeout(2000)
            save_screenshot(page, "create_10_workflow_detail")

        # ============================================
        # TEST 4: TRY THE DEMO WORKFLOW BUILDER
        # ============================================
        print("\n=== TEST DEMO WORKFLOW BUILDER ===")

        page.goto("https://swarmsync.ai/demo/workflows", wait_until="networkidle")
        page.wait_for_timeout(2000)

        # Click on a template
        templates = page.locator("[class*='template'], [class*='card']").all()
        if templates:
            print(f"Found {len(templates)} templates")
            templates[0].click()
            page.wait_for_timeout(2000)
            save_screenshot(page, "create_11_demo_template_selected")

            # Check if JSON populated
            json_area = page.locator("textarea, [class*='editor'], pre").first
            if json_area and json_area.is_visible():
                json_content = json_area.inner_text() or json_area.input_value()
                if json_content and len(json_content) > 10:
                    results["demo_workflow"] = {"template_loaded": True}
                    print("Template JSON loaded!")

        browser.close()

    # Save results
    results_path = f"{SCREENSHOTS_DIR}/create_flows_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_path}")

    print("\n" + "=" * 60)
    print("CREATE FLOWS TEST COMPLETE")
    print("=" * 60)

    return results

if __name__ == "__main__":
    main()
