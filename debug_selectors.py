"""
Debug script: opens the Cathay Pacific homepage with Playwright Inspector so you
can find the correct selectors interactively.

Run: python debug_selectors.py
Then use the Inspector to click elements and see their selectors.
"""
from playwright.sync_api import sync_playwright

HOME = "https://www.cathaypacific.com/cx/en_US.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    context = browser.new_context()
    page = context.new_page()

    print("Opening homepage...")
    page.goto(HOME, timeout=30000)
    page.wait_for_load_state("networkidle", timeout=20000)

    # Accept cookies if present
    try:
        btn = page.locator('button:has-text("Accept All"), button:has-text("Accept Cookies")').first
        btn.click(timeout=4000)
        print("Accepted cookies")
    except Exception:
        print("No cookie banner")

    print("\n=== HOMEPAGE LOADED ===")
    print("Task 1: Find the 'Redeem with miles' toggle.")
    print("Right-click it in the browser and choose Inspect.")
    print("Note the HTML — we need a unique CSS selector or text.")
    input("Press Enter after you've noted the toggle selector...")

    print("\nTask 2: Click the 'Redeem with miles' toggle manually.")
    input("Press Enter after you've clicked the toggle...")

    print("\nTask 3: Find the 'Sign in' link/button in the header.")
    input("Press Enter after you've noted the sign-in selector...")

    print("\nClicking what we hope is the sign-in button...")
    try:
        page.locator('a:has-text("Sign in"), button:has-text("Sign in")').first.click(timeout=5000)
        page.wait_for_load_state("networkidle", timeout=15000)
        print("Navigated. Current URL:", page.url)
    except Exception as e:
        print("Could not click sign-in:", e)

    print("\nTask 4: Find the phone/member number input on the login page.")
    print("Right-click it → Inspect and note the selector.")
    input("Press Enter after you've noted the phone input selector...")

    print("\nType your credentials manually in the browser if you want.")
    print("Watch the URL and page changes.")
    input("Press Enter when done (or Ctrl+C to exit)...")

    browser.close()
    print("Done.")
