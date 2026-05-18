"""
Opens the browser and records ALL network calls while you interact manually.
You do the clicking, I capture the API calls.
"""
import json
from playwright.sync_api import sync_playwright

HOME = "https://www.cathaypacific.com/cx/en_US.html"
captured = []

def handle_request(request):
    url = request.url
    if any(x in url for x in ["book.cathaypacific", "api", "search", "avail", "award", "flight", "redeem", "miles", "offer"]):
        entry = {"method": request.method, "url": url}
        if request.post_data:
            entry["post_data"] = request.post_data
        captured.append(entry)

def handle_response(response):
    url = response.url
    if any(x in url for x in ["book.cathaypacific", "api", "search", "avail", "award", "flight", "redeem", "miles", "offer"]):
        try:
            body = response.json()
            for item in captured:
                if item["url"] == url and "response" not in item:
                    item["response"] = body
                    break
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

    page.goto(HOME, timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    print("=== Browser is open ===")
    print()
    print("Please do these steps in the browser:")
    print("  1. Accept the cookie banner if it appears")
    print("  2. Click the 'Redeem with miles' toggle")
    print("  3. Fill in: From = CGO (Zhengzhou), To = JFK (New York)")
    print("  4. Select One Way, Economy")
    print("  5. Pick any date in July 2026")
    print("  6. Click the search/sign-in button")
    print("  7. Log in with your credentials if prompted")
    print("  8. Wait for results to fully load")
    print()
    input("Press Enter AFTER results are showing (or after login redirects)...")

    page.screenshot(path="session_result.png")
    print("Saved session_result.png")

    with open("session_api.json", "w") as f:
        json.dump(captured, f, indent=2)
    print(f"\nCaptured {len(captured)} API calls -> session_api.json")
    print("\nKey URLs captured:")
    for item in captured:
        if "book.cathaypacific" in item["url"]:
            print(f"  {item['method']} {item['url'][:120]}")

    browser.close()
