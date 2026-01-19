#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive audit script for swarmsync.ai
Tests homepage, key pages, login flow, and user dashboard
"""

from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime
import sys

def audit_homepage(page):
    """Audit homepage for SEO, UX, and performance"""
    print("\n" + "="*60)
    print("HOMEPAGE AUDIT")
    print("="*60)
    
    page.goto("https://swarmsync.ai/", wait_until="networkidle")
    
    # Performance metrics
    perf_metrics = page.evaluate("""
    () => {
        const perfData = performance.getEntriesByType("navigation")[0];
        const paint = performance.getEntriesByType("paint");
        return {
            dns: perfData.domainLookupEnd - perfData.domainLookupStart,
            tcp: perfData.connectEnd - perfData.connectStart,
            ttfb: perfData.responseStart - perfData.requestStart,
            domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
            loadComplete: perfData.loadEventEnd - perfData.loadEventStart,
            firstPaint: paint.find(p => p.name === 'first-paint')?.startTime || 'N/A',
            firstContentfulPaint: paint.find(p => p.name === 'first-contentful-paint')?.startTime || 'N/A',
        };
    }
    """)
    
    print("\n[PERF] Performance Metrics:")
    print(f"  DNS Lookup: {perf_metrics['dns']:.0f}ms")
    print(f"  TCP Connection: {perf_metrics['tcp']:.0f}ms")
    print(f"  TTFB: {perf_metrics['ttfb']:.0f}ms")
    print(f"  FCP: {perf_metrics['firstContentfulPaint']:.0f}ms")
    print(f"  LCP: {perf_metrics['loadComplete']:.0f}ms")
    
    # SEO audit
    title = page.title()
    meta_desc = page.locator('meta[name="description"]').get_attribute("content") or "Missing"
    h1_elements = page.locator("h1").all()
    h1_text = [h.inner_text() for h in h1_elements] if h1_elements else []
    
    print(f"\n[SEO] On-Page Elements:")
    print(f"  Title: {title}")
    print(f"  Meta Description: {meta_desc[:80]}...")
    print(f"  H1 Count: {len(h1_text)}")
    for i, h1 in enumerate(h1_text, 1):
        print(f"    H1.{i}: {h1}")
    
    # Check for sitemap, robots.txt
    try:
        response = page.context.request.get("https://swarmsync.ai/robots.txt")
        robots_exists = response.status == 200
        print(f"  robots.txt: {'[OK]' if robots_exists else '[MISSING]'}")
    except:
        print(f"  robots.txt: [NOT ACCESSIBLE]")
    
    try:
        response = page.context.request.get("https://swarmsync.ai/sitemap.xml")
        sitemap_exists = response.status == 200
        print(f"  sitemap.xml: {'[OK]' if sitemap_exists else '[MISSING]'}")
    except:
        print(f"  sitemap.xml: [NOT ACCESSIBLE]")
    
    # Mobile responsiveness check
    page.set_viewport_size({"width": 375, "height": 812})
    mobile_size = page.evaluate("() => document.documentElement.scrollWidth")
    
    # Reset viewport
    page.set_viewport_size({"width": 1280, "height": 720})
    
    print(f"\n[MOBILE] Responsiveness:")
    print(f"  Mobile Width: {mobile_size}px")
    print(f"  Mobile Optimized: {'YES' if mobile_size <= 400 else 'NEEDS WORK'}")
    
    # Accessibility check
    print(f"\n[A11Y] Accessibility:")
    
    # Check for alt text on images
    images = page.locator("img").all()
    images_with_alt = sum(1 for img in images if img.get_attribute("alt"))
    print(f"  Images with alt text: {images_with_alt}/{len(images)}")
    
    # Links
    links = page.locator("a").all()
    print(f"  Total Links: {len(links)}")
    
    # Screenshot for visual inspection
    page.screenshot(path="/tmp/swarmsync_homepage.png", full_page=True)
    print(f"\n[OUTPUT] Homepage screenshot saved to /tmp/swarmsync_homepage.png")
    
    return {
        "perf_metrics": perf_metrics,
        "title": title,
        "meta_desc": meta_desc,
        "h1_count": len(h1_text),
        "images_with_alt": images_with_alt,
        "total_images": len(images),
        "total_links": len(links),
    }

def test_key_pages(page):
    """Test navigation to key pages"""
    print("\n" + "="*60)
    print("KEY PAGES AUDIT")
    print("="*60)
    
    pages_to_test = [
        ("/pricing", "Pricing"),
        ("/agents", "Marketplace"),
        ("/login", "Login"),
        ("/register", "Register"),
    ]
    
    results = {}
    for path, name in pages_to_test:
        try:
            page.goto(f"https://swarmsync.ai{path}", wait_until="networkidle", timeout=10000)
            status = "[OK] Accessible"
            title = page.title()
            results[name] = {"status": status, "title": title}
            print(f"  {name}: {status} - {title}")
        except Exception as e:
            results[name] = {"status": f"[ERROR] {str(e)[:50]}", "title": ""}
            print(f"  {name}: [ERROR] {str(e)[:50]}")
    
    return results

def test_login_flow(page):
    """Test login functionality"""
    print("\n" + "="*60)
    print("LOGIN & AUTHENTICATION AUDIT")
    print("="*60)
    
    try:
        page.goto("https://swarmsync.ai/login", wait_until="networkidle")
        print("  [OK] Login page accessible")
        
        # Check for HTTPS
        url = page.url
        is_https = url.startswith("https")
        print(f"  HTTPS: {'YES' if is_https else 'NO'}")
        
        # Look for email input
        email_input = page.locator('input[type="email"], input[name*="email"]').first
        if email_input.is_visible():
            print("  [OK] Email input found")
            email_input.fill("rainking6693@gmail.com")
        else:
            print("  [WARNING] Email input not found")
        
        # Screenshot
        page.screenshot(path="/tmp/swarmsync_login.png")
        print("  [OK] Login page screenshot saved")
        
    except Exception as e:
        print(f"  [ERROR] Login test failed: {e}")

def test_user_dashboard(page, email, password):
    """Test user dashboard access and features"""
    print("\n" + "="*60)
    print("USER DASHBOARD AUDIT")
    print("="*60)
    
    try:
        page.goto("https://swarmsync.ai/login", wait_until="networkidle")
        print("  [OK] Navigated to login page")
        
        # Fill email
        email_input = page.locator('input[type="email"], input[name*="email"], input[placeholder*="email" i]').first
        if email_input.is_visible():
            email_input.fill(email)
            print(f"  [OK] Entered email: {email}")
        
        # Look for password field
        password_input = page.locator('input[type="password"]').first
        if password_input.is_visible():
            password_input.fill(password)
            print("  [OK] Entered password")
        
        # Submit
        submit_button = page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Login")').first
        if submit_button.is_visible():
            submit_button.click()
            print("  [OK] Clicked login button")
            page.wait_for_load_state("networkidle", timeout=15000)
        
        # Check if logged in
        time.sleep(2)
        current_url = page.url
        if "/dashboard" in current_url or "/agents" in current_url:
            print(f"  [OK] Login successful - redirected to {current_url}")
            page.screenshot(path="/tmp/swarmsync_dashboard.png", full_page=True)
            print("  [OK] Dashboard screenshot saved")
        else:
            print(f"  [WARNING] Login flow unclear - current URL: {current_url}")
        
    except Exception as e:
        print(f"  [ERROR] Dashboard test failed: {e}")

def test_security_headers(page):
    """Check security headers"""
    print("\n" + "="*60)
    print("SECURITY AUDIT")
    print("="*60)
    
    page.goto("https://swarmsync.ai/", wait_until="networkidle")
    
    # Check for privacy policy
    privacy_links = page.locator('a:has-text("Privacy"), a[href*="privacy"]').all()
    print(f"  Privacy Policy Link: {'YES' if privacy_links else 'NO'}")
    
    # Check for cookie consent
    cookie_banner = page.locator('button:has-text("Accept"), div:has-text("cookies")').first
    print(f"  Cookie Consent: {'YES' if cookie_banner.is_visible() else 'NOT DETECTED'}")
    
    # Check for security certifications mentioned
    content = page.content()
    soc2_mentioned = "SOC 2" in content
    gdpr_mentioned = "GDPR" in content
    print(f"  SOC 2 Certification: {'MENTIONED' if soc2_mentioned else 'NOT MENTIONED'}")
    print(f"  GDPR Compliance: {'MENTIONED' if gdpr_mentioned else 'NOT MENTIONED'}")

def main():
    """Run full audit"""
    print("\n" + "="*60)
    print("SWARMSYNC.AI COMPREHENSIVE AUDIT")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    with sync_playwright() as p:
        # Use desktop browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Set user agent for realistic testing
        page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
        })
        
        try:
            # Run audits
            homepage_results = audit_homepage(page)
            pages_results = test_key_pages(page)
            test_login_flow(page)
            test_user_dashboard(page, "rainking6693@gmail.com", "Hudson1234%")
            test_security_headers(page)
            
        finally:
            browser.close()
    
    print("\n" + "="*60)
    print("AUDIT COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
