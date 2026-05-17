import logging
import re
import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from config_loader import Config, Route

logger = logging.getLogger(__name__)

AWARD_SEARCH_URL = "https://www.cathaypacific.com/cx/en_US/book-a-trip/redeem-miles.html"

# All site selectors in one place — update these after running selector verification against the live site.
SELECTORS = {
    "cookie_accept": 'button:has-text("Accept All"), button:has-text("Accept Cookies"), button:has-text("I Accept")',
    "one_way": 'label:has-text("One way"), input[value*="oneway"], input[value*="OW"]',
    "origin_input": '[data-testid*="origin"], [aria-label*="Origin"], [aria-label*="From"], input[placeholder*="From"]',
    "origin_option": '[role="option"]:has-text("{code}"), li:has-text("{code}")',
    "destination_input": '[data-testid*="destination"], [aria-label*="Destination"], [aria-label*="To"], input[placeholder*="To"]',
    "destination_option": '[role="option"]:has-text("{code}"), li:has-text("{code}")',
    "date_input": '[data-testid*="depart"], [aria-label*="Depart"], [aria-label*="Date"], input[placeholder*="Date"]',
    "search_button": 'button:has-text("Search"), button[type="submit"]:has-text("Search")',
    "captcha": '[class*="captcha"], [id*="captcha"], [class*="recaptcha"], iframe[src*="recaptcha"]',
    "login_wall": '[class*="login-required"], [class*="signin-wall"], a:has-text("Sign in to continue")',
    "flight_card": '[class*="flight-card"], [class*="result-item"], [data-testid*="flight"]',
    "miles_price": '[class*="miles"], [class*="award-price"], [class*="redeem"]',
}


@dataclass
class AvailableAward:
    date: date
    route: Route
    miles_required: Optional[int]


def check_all(config: Config) -> List[AvailableAward]:
    results = []
    dates = _date_range(config.date_start, config.date_end)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=config.headless)
        try:
            for route in config.routes:
                for d in dates:
                    awards = _check_one(browser, route, d, config.headless)
                    results.extend(awards)
                    time.sleep(2)  # polite delay between requests
        finally:
            browser.close()
    return results


def _date_range(start: date, end: date) -> List[date]:
    result = []
    current = start
    while current <= end:
        result.append(current)
        current += timedelta(days=1)
    return result


def _check_one(browser, route: Route, travel_date: date, headless: bool) -> List[AvailableAward]:
    page = browser.new_page()
    try:
        logger.info("Checking %s->%s on %s", route.origin, route.destination, travel_date)
        page.goto(AWARD_SEARCH_URL, timeout=30000)
        _dismiss_cookie_banner(page)

        if _has_captcha(page):
            logger.warning("CAPTCHA detected for %s->%s on %s — skipping", route.origin, route.destination, travel_date)
            return []

        _fill_search_form(page, route, travel_date)
        _submit_search(page)

        if _has_captcha(page):
            logger.warning("CAPTCHA after search for %s->%s on %s — skipping", route.origin, route.destination, travel_date)
            return []

        return _parse_results(page, route, travel_date)

    except PlaywrightTimeoutError:
        logger.warning("Timeout checking %s->%s on %s", route.origin, route.destination, travel_date)
        return []
    except Exception as e:
        logger.error("Unexpected error checking %s->%s on %s: %s", route.origin, route.destination, travel_date, e)
        return []
    finally:
        page.close()


def _dismiss_cookie_banner(page) -> None:
    try:
        page.locator(SELECTORS["cookie_accept"]).first.click(timeout=4000)
        logger.debug("Cookie banner dismissed.")
    except Exception:
        pass


def _has_captcha(page) -> bool:
    try:
        return page.locator(SELECTORS["captcha"]).count() > 0
    except Exception:
        return False


def _fill_search_form(page, route: Route, travel_date: date) -> None:
    page.locator(SELECTORS["one_way"]).first.click(timeout=8000)

    origin_input = page.locator(SELECTORS["origin_input"]).first
    origin_input.fill(route.origin)
    page.locator(SELECTORS["origin_option"].format(code=route.origin)).first.click(timeout=8000)

    dest_input = page.locator(SELECTORS["destination_input"]).first
    dest_input.fill(route.destination)
    page.locator(SELECTORS["destination_option"].format(code=route.destination)).first.click(timeout=8000)

    date_input = page.locator(SELECTORS["date_input"]).first
    date_input.fill(travel_date.strftime("%d/%m/%Y"))


def _submit_search(page) -> None:
    page.locator(SELECTORS["search_button"]).first.click(timeout=8000)
    page.wait_for_load_state("networkidle", timeout=30000)


def _parse_results(page, route: Route, travel_date: date) -> List[AvailableAward]:
    if page.locator(SELECTORS["login_wall"]).count() > 0:
        logger.warning("Login wall detected for %s->%s — skipping", route.origin, route.destination)
        return []

    results = []
    cards = page.locator(SELECTORS["flight_card"]).all()

    if not cards:
        logger.info("No flight cards found for %s->%s on %s", route.origin, route.destination, travel_date)
        return []

    for card in cards:
        try:
            miles_text = card.locator(SELECTORS["miles_price"]).first.inner_text(timeout=3000)
            miles = _parse_miles(miles_text)
            if miles is not None:
                results.append(AvailableAward(date=travel_date, route=route, miles_required=miles))
        except Exception:
            continue

    logger.info("Found %d award(s) for %s->%s on %s", len(results), route.origin, route.destination, travel_date)
    return results


def _parse_miles(text: str) -> Optional[int]:
    if not text:
        return None
    text = text.strip().replace(",", "")
    m = re.search(r"(\d+)[Kk]", text)
    if m:
        return int(m.group(1)) * 1000
    m = re.search(r"(\d+)", text)
    if m:
        val = int(m.group(1))
        return val if val > 100 else None  # ignore small numbers like seat counts
    return None
