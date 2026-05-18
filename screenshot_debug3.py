"""
Step 3: Click the 'Redeem with miles' toggle and capture the award search API.
"""
import json
from playwright.sync_api import sync_playwright

HOME = "https://www.cathaypacific.com/cx/en_US.html"
captured = []

def handle_request(request):
    url = request.url
    if "book.cathaypacific.com" in url:
        captured.append({"method": request.method, "url": url, "post_data": request.post_data})

def handle_response(response):
    url = response.url
    if "book.cathaypacific.com" in url:
        try:
            body = response.json()
            for item in captured:
                if item["url"] == url and "response" not in item:
                    item["response"] = body
        except Exception:
            pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
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
    page.evaluate("window.scrollTo(0, 400)")
    page.wait_for_timeout(1000)

    # Find and click the Redeem with miles toggle
    # It's a toggle/switch element near the text "Redeem with miles"
    toggle_selectors = [
        'label:has-text("Redeem with miles")',
        'span:has-text("Redeem with miles")',
        '[class*="toggle"]:has-text("Redeem")',
        'input[type="checkbox"] + label:has-text("Redeem")',
        '.c-toggle:has-text("Redeem")',
        'button:has-text("Redeem with miles")',
    ]

    clicked = False
    for sel in toggle_selectors:
        try:
            el = page.locator(sel).first
            if el.count() > 0:
                el.click(timeout=3000)
                print(f"Clicked toggle with selector: {sel}")
                clicked = True
                break
        except Exception:
            continue

    if not clicked:
        # Dump all elements containing "Redeem" text
        all_with_redeem = page.locator(':has-text("Redeem with miles")').all()
        print(f"Elements containing 'Redeem with miles': {len(all_with_redeem)}")
        for el in all_with_redeem[:5]:
            try:
                tag = el.evaluate('el => el.tagName')
                cls = el.get_attribute('class') or ''
                print(f"  {tag} class='{cls[:80]}'")
            except Exception:
                pass

    page.wait_for_timeout(2000)
    page.screenshot(path="s4_toggle_clicked.png")
    print("Saved s4_toggle_clicked.png")

    # Now try filling the award search form
    # Try origin field
    try:
        origin_input = page.locator('input[placeholder*="From"], input[placeholder*="from"], [aria-label*="From"], [aria-label*="Origin"]').first
        origin_input.fill("CGO")
        page.wait_for_timeout(1000)
        page.screenshot(path="s5_origin_typed.png")
        print("Saved s5_origin_typed.png")

        # Click first dropdown option
        page.locator('[role="option"]:has-text("CGO"), li:has-text("Zhengzhou")').first.click(timeout=5000)
        page.wait_for_timeout(500)
    except Exception as e:
        print(f"Origin input: {e}")

    page.screenshot(path="s6_form_state.png")
    print("Saved s6_form_state.png")

    with open("captured_api3.json", "w") as f:
        json.dump(captured, f, indent=2)
    print(f"\nCaptured {len(captured)} book.cathaypacific.com calls")
    for item in captured[:10]:
        print(f"  {item['method']} {item['url']}")

    browser.close()
