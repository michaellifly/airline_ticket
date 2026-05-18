"""
Intercepts network requests while you manually search for award flights.
Run this, log in and do ONE search in the browser, then press Enter.
The script will print all API calls it captured.
"""
import json
from playwright.sync_api import sync_playwright

HOME = "https://www.cathaypacific.com/cx/en_US.html"

captured = []

def handle_request(request):
    url = request.url
    if any(x in url for x in ["api", "search", "avail", "award", "flight", "redeem", "book"]):
        captured.append({
            "method": request.method,
            "url": url,
            "headers": dict(request.headers),
            "post_data": request.post_data,
        })

def handle_response(response):
    url = response.url
    if any(x in url for x in ["api", "search", "avail", "award", "flight", "redeem", "book"]):
        try:
            body = response.json()
            for item in captured:
                if item["url"] == url:
                    item["response"] = body
        except Exception:
            pass

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        slow_mo=100,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800},
        locale="en-US",
    )
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    page = context.new_page()

    page.on("request", handle_request)
    page.on("response", handle_response)

    print("Opening Cathay Pacific homepage...")
    page.goto(HOME, timeout=30000)

    print("\n=== Browser is open ===")
    print("1. Log in to your Cathay Pacific account")
    print("2. Click 'Redeem with miles'")
    print("3. Search CGO -> JFK for any date in July 2026")
    print("4. Wait for results to load")
    print("5. Come back here and press Enter")
    input("\nPress Enter when results are showing...")

    browser.close()

print(f"\nCaptured {len(captured)} API calls:\n")
for i, req in enumerate(captured, 1):
    print(f"--- Call {i} ---")
    print(f"  {req['method']} {req['url']}")
    if req.get("post_data"):
        try:
            pd = json.loads(req["post_data"])
            print(f"  Body: {json.dumps(pd, indent=2)[:500]}")
        except Exception:
            print(f"  Body: {req['post_data'][:200]}")
    if req.get("response"):
        r = json.dumps(req["response"])
        print(f"  Response: {r[:300]}")
    print()

with open("captured_api.json", "w") as f:
    json.dump(captured, f, indent=2)
print("Full results saved to captured_api.json")
