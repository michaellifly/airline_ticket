"""
Step 2: Click the 'Redeem with miles' tab in the booking widget and inspect the award search form.
"""
import json
from playwright.sync_api import sync_playwright

HOME = "https://www.cathaypacific.com/cx/en_US.html"
captured = []

def handle_request(request):
    url = request.url
    if "book.cathaypacific.com" in url or any(x in url for x in ["award", "redeem", "miles", "avail"]):
        captured.append({
            "method": request.method,
            "url": url,
            "post_data": request.post_data,
        })

def handle_response(response):
    url = response.url
    if "book.cathaypacific.com" in url or any(x in url for x in ["award", "redeem", "miles", "avail"]):
        try:
            body = response.json()
            for item in captured:
                if item["url"] == url and "response" not in item:
                    item["response"] = body
        except Exception:
            pass

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
    page.on("request", handle_request)
    page.on("response", handle_response)

    print("Navigating...")
    page.goto(HOME, timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # Accept cookies
    try:
        page.locator('button:has-text("Accept All"), button:has-text("Accept Cookies")').first.click(timeout=4000)
        page.wait_for_timeout(1000)
    except Exception:
        pass

    # Scroll to booking widget
    page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
    page.wait_for_timeout(1000)
    page.screenshot(path="s1_widget_area.png")
    print("Saved s1_widget_area.png")

    # Try clicking Redeem with miles tab
    try:
        page.locator('text="Redeem with miles"').first.click(timeout=5000)
        page.wait_for_timeout(2000)
        page.screenshot(path="s2_redeem_tab.png")
        print("Saved s2_redeem_tab.png - Redeem tab clicked")
    except Exception as e:
        print(f"Could not click exact text: {e}")
        # Try partial text
        try:
            page.locator('text=Redeem').first.click(timeout=5000)
            page.wait_for_timeout(2000)
            page.screenshot(path="s2_redeem_tab.png")
            print("Saved s2_redeem_tab.png - Redeem (partial) clicked")
        except Exception as e2:
            print(f"Could not click Redeem at all: {e2}")

    # Print all links/buttons with "redeem" or "miles" in them
    elements = page.locator('[class*="redeem"], [class*="miles"], [class*="award"], a:has-text("Redeem"), button:has-text("Redeem")').all()
    print(f"\nFound {len(elements)} redeem/miles/award elements:")
    for el in elements[:10]:
        try:
            print(f"  tag={el.evaluate('el => el.tagName')}, class={el.get_attribute('class')}, text={el.inner_text()[:50]}")
        except Exception:
            pass

    # Full screenshot at end
    page.screenshot(path="s3_final.png", full_page=True)
    print("\nSaved s3_final.png (full page)")

    with open("captured_api2.json", "w") as f:
        json.dump(captured, f, indent=2)
    print(f"Captured {len(captured)} book.cathaypacific.com API calls -> captured_api2.json")

    browser.close()
