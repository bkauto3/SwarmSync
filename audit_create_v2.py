"""
SwarmSync - Actually Create Agent and Workflow
"""
from playwright.sync_api import sync_playwright
import json
import os
from datetime import datetime

SCREENSHOTS_DIR = "C:/Users/Ben/Desktop/Github/Agent-Market/audit_screenshots"

def save_screenshot(page, name):
    path = f"{SCREENSHOTS_DIR}/{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"Screenshot: {path}")
    return path

def main():
    print("=" * 60)
    print("SwarmSync - Create Agent & Workflow v2")
    print("=" * 60)

    results = {"agent": {}, "workflow": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        # Login
        print("\n=== LOGIN ===")
        page.goto("https://swarmsync.ai/login", wait_until="networkidle")
        page.wait_for_timeout(2000)
        page.locator("input[type='email']").first.fill("rainking6693@gmail.com")
        page.locator("input[type='password']").first.fill("Hudson1234%")
        page.locator("button[type='submit']").first.click()
        page.wait_for_timeout(5000)
        print(f"Logged in, URL: {page.url}")

        # ============================================
        # CREATE AGENT
        # ============================================
        print("\n=== CREATE AGENT ===")
        page.goto("https://swarmsync.ai/agents/new", wait_until="networkidle")
        page.wait_for_timeout(3000)
        save_screenshot(page, "agent_01_form")

        # Fill Step 1: Agent Details
        print("Filling agent details...")

        # Agent name - find the input field
        name_inputs = page.locator("input").all()
        for inp in name_inputs:
            placeholder = inp.get_attribute("placeholder") or ""
            if "apollo" in placeholder.lower() or "name" in placeholder.lower():
                inp.fill("Audit Test Agent")
                print("Filled agent name")
                break

        # Description textarea
        desc_areas = page.locator("textarea").all()
        for textarea in desc_areas:
            placeholder = textarea.get_attribute("placeholder") or ""
            if "describe" in placeholder.lower() or "desc" in placeholder.lower():
                textarea.fill("This is a test agent created during the SwarmSync audit on 2026-01-02. It demonstrates the agent creation flow.")
                print("Filled description")
                break

        # Select visibility (Public is default, click it to ensure)
        public_btn = page.locator("button:has-text('Public'), [class*='button']:has-text('Public')").first
        if public_btn and public_btn.is_visible():
            public_btn.click()
            print("Selected Public visibility")

        save_screenshot(page, "agent_02_details_filled")

        # Click Next to go to step 2
        next_btn = page.locator("button:has-text('Next')").first
        if next_btn and next_btn.is_visible():
            next_btn.click()
            page.wait_for_timeout(2000)
            save_screenshot(page, "agent_03_step2_capabilities")
            print("Moved to Step 2: Capabilities & Pricing")

            # Fill Step 2 if there are fields
            # Look for category/skills inputs
            category_input = page.locator("input[placeholder*='category' i], select").first
            if category_input and category_input.is_visible():
                try:
                    category_input.fill("Research")
                    print("Filled category")
                except:
                    pass

            # Click Next to step 3
            next_btn = page.locator("button:has-text('Next')").first
            if next_btn and next_btn.is_visible():
                next_btn.click()
                page.wait_for_timeout(2000)
                save_screenshot(page, "agent_04_step3_schema")
                print("Moved to Step 3: AP2 Schema")

                # Click Next to step 4
                next_btn = page.locator("button:has-text('Next')").first
                if next_btn and next_btn.is_visible():
                    next_btn.click()
                    page.wait_for_timeout(2000)
                    save_screenshot(page, "agent_05_step4_budgets")
                    print("Moved to Step 4: Budgets & Guardrails")

                    # Look for final submit/create button
                    create_btn = page.locator("button:has-text('Create'), button:has-text('Launch'), button:has-text('Submit'), button:has-text('Save')").first
                    if create_btn and create_btn.is_visible():
                        print("Found Create button, clicking...")
                        create_btn.click()
                        page.wait_for_timeout(5000)
                        save_screenshot(page, "agent_06_after_create")
                        results["agent"]["submitted"] = True
                        results["agent"]["final_url"] = page.url
                        print(f"After create: {page.url}")

                        # Check for success/error
                        if "/agents/" in page.url and "/new" not in page.url:
                            results["agent"]["success"] = True
                            print("Agent created successfully!")
                        else:
                            error = page.locator("[class*='error'], [class*='alert']").first
                            if error and error.is_visible():
                                results["agent"]["error"] = error.inner_text()
                                print(f"Error: {error.inner_text()}")

        # ============================================
        # CREATE WORKFLOW
        # ============================================
        print("\n=== CREATE WORKFLOW ===")
        page.goto("https://swarmsync.ai/console/workflows", wait_until="networkidle")
        page.wait_for_timeout(3000)
        save_screenshot(page, "workflow_01_page")

        # Fill workflow details
        print("Filling workflow details...")

        # Workflow name - look for input with "Sample orchestration" or name placeholder
        all_inputs = page.locator("input").all()
        for inp in all_inputs:
            value = inp.input_value()
            placeholder = inp.get_attribute("placeholder") or ""
            if "sample" in value.lower() or "orchestration" in value.lower() or "name" in placeholder.lower():
                inp.clear()
                inp.fill("Audit Test Workflow")
                print("Filled workflow name")
                break

        # Budget input
        budget_inputs = page.locator("input[type='number'], input[placeholder*='budget' i]").all()
        for inp in budget_inputs:
            try:
                inp.clear()
                inp.fill("50")
                print("Filled budget: 50")
                break
            except:
                pass

        # Description
        desc_textareas = page.locator("textarea").all()
        for textarea in desc_textareas:
            try:
                textarea.clear()
                textarea.fill("Audit test workflow - multi-stage research and analysis flow created during site audit.")
                print("Filled workflow description")
                break
            except:
                pass

        save_screenshot(page, "workflow_02_details_filled")

        # Try to add a step
        add_step_btn = page.locator("button:has-text('Add Step')").first
        if add_step_btn and add_step_btn.is_visible():
            print("Clicking Add Step...")
            add_step_btn.click()
            page.wait_for_timeout(2000)
            save_screenshot(page, "workflow_03_add_step_clicked")

            # Check if modal/form appeared for step
            step_inputs = page.locator("[class*='modal'] input, [class*='dialog'] input, [class*='step'] input").all()
            if step_inputs:
                print(f"Found {len(step_inputs)} step inputs")
                # Try to fill step details
                for inp in step_inputs:
                    placeholder = inp.get_attribute("placeholder") or ""
                    name = inp.get_attribute("name") or ""
                    if "agent" in placeholder.lower() or "agent" in name.lower():
                        inp.fill("research-agent")
                    elif "name" in placeholder.lower() or "name" in name.lower():
                        inp.fill("Research Step")

                save_screenshot(page, "workflow_04_step_filled")

                # Save the step
                save_step_btn = page.locator("button:has-text('Save'), button:has-text('Add'), button:has-text('Confirm')").first
                if save_step_btn and save_step_btn.is_visible():
                    save_step_btn.click()
                    page.wait_for_timeout(2000)
                    save_screenshot(page, "workflow_05_step_saved")

        # Create the workflow
        create_workflow_btn = page.locator("button:has-text('Create Workflow')").first
        if create_workflow_btn and create_workflow_btn.is_visible():
            print("Clicking Create Workflow...")
            create_workflow_btn.click()
            page.wait_for_timeout(5000)
            save_screenshot(page, "workflow_06_after_create")
            results["workflow"]["submitted"] = True
            results["workflow"]["final_url"] = page.url
            print(f"After create: {page.url}")

            # Check for success message or new workflow
            success = page.locator("[class*='success'], [class*='toast']").first
            if success and success.is_visible():
                results["workflow"]["success"] = True
                results["workflow"]["message"] = success.inner_text()
                print(f"Success: {success.inner_text()}")

            error = page.locator("[class*='error'], [class*='alert']").first
            if error and error.is_visible():
                results["workflow"]["error"] = error.inner_text()
                print(f"Error: {error.inner_text()}")

            # Check existing workflows section
            page.wait_for_timeout(2000)
            page.reload()
            page.wait_for_timeout(3000)
            save_screenshot(page, "workflow_07_after_reload")

        browser.close()

    # Save results
    results_path = f"{SCREENSHOTS_DIR}/create_v2_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults: {json.dumps(results, indent=2)}")

    print("\n" + "=" * 60)
    print("CREATE TEST v2 COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
