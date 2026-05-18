"""
Takes screenshots at each step so Claude can see the page.
Run headless so it works without display interaction.
"""
import json
from playwright.sync_api import sync_playwright

HOME = "https://www.cathaypacific.com/cx/en_US.html"

captured = []

def handle_response(response):
    url = response.url
    if any(x in url for x in ["api", "search", "avail", "award", "flight", "redeem", "book", "offer"]):
        try:
            body = response.json()
            captured.append({"url": url, "response": body})
        except Exception:
            captured.append({"url": url, "response": None})

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 900},
        locale="en-US",
    )
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    page = context.new_page()
    page.on("response", handle_response)

    print("Navigating to homepage...")
    page.goto(HOME, timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    page.screenshot(path="screenshot_01_homepage.png", full_page=False)
    print("Saved screenshot_01_homepage.png")

    # Accept cookies
    try:
        page.locator('button:has-text("Accept All"), button:has-text("Accept Cookies")').first.click(timeout=4000)
        page.wait_for_timeout(1000)
        page.screenshot(path="screenshot_02_after_cookies.png")
        print("Saved screenshot_02_after_cookies.png")
    except Exception:
        print("No cookie banner")

    # Try clicking Redeem with miles
    try:
        page.locator('text=Redeem').first.click(timeout=5000)
        page.wait_for_timeout(1000)
        page.screenshot(path="screenshot_03_after_redeem_click.png")
        print("Saved screenshot_03_after_redeem_click.png")
    except Exception as e:
        print(f"Could not click Redeem: {e}")
        page.screenshot(path="screenshot_03_redeem_failed.png")
        print("Saved screenshot_03_redeem_failed.png")

    # Dump the page HTML to inspect structure
    html = page.content()
    with open("page_html.txt", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved page_html.txt")

    # Save any captured API calls
    with open("captured_api.json", "w") as f:
        json.dump(captured, f, indent=2)
    print(f"Captured {len(captured)} API calls -> captured_api.json")

    browser.close()
print("Done.")
