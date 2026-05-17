# Cathay Pacific Miles Checker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scheduled Python service that checks Cathay Pacific's website for economy award seat availability on configured routes/dates and sends Telegram notifications when seats are found.

**Architecture:** A single Python process with four modules — config loader, Playwright-based checker, Telegram notifier via HTTP, and APScheduler — wired together in `main.py`. All configuration lives in a `config.yaml` file bound-mounted into the Docker container at runtime.

**Tech Stack:** Python 3.12, Playwright (sync API, Chromium), APScheduler 3.x (BlockingScheduler), requests (Telegram HTTP calls), PyYAML, Docker + Docker Compose, Ubuntu 22.04 ARM64 (Oracle Cloud Free Tier).

---

## File Map

| File | Responsibility |
|---|---|
| `config_loader.py` | Parse and validate `config.yaml` into typed dataclasses |
| `checker.py` | Playwright automation: navigate CX site, fill form, parse results |
| `notifier.py` | Send Telegram messages via Telegram Bot HTTP API |
| `scheduler.py` | APScheduler setup: run job immediately + on interval |
| `main.py` | Entry point: load config, wire modules, start scheduler |
| `requirements.txt` | Pinned dependencies |
| `config.yaml.example` | Committed template (no real credentials) |
| `Dockerfile` | ARM64-compatible image with Playwright + Chromium |
| `docker-compose.yml` | Bind-mount config, restart policy, log limits |
| `tests/test_config_loader.py` | Config loading and validation tests |
| `tests/test_notifier.py` | Telegram send logic tests (mock requests) |
| `tests/test_checker.py` | Checker unit tests (mock Playwright, pure functions) |

---

## Task 1: Project scaffold, dependencies, and config loader

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml.example`
- Modify: `.gitignore`
- Create: `config_loader.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config_loader.py`

- [ ] **Step 1: Create `requirements.txt`**

```
playwright==1.44.0
apscheduler==3.10.4
pyyaml==6.0.1
requests==2.32.3
pytest==8.2.0
pytest-mock==3.14.0
```

- [ ] **Step 2: Create `config.yaml.example`**

```yaml
routes:
  - origin: CGO
    destination: JFK
    cabin: economy

dates:
  start: "2026-07-01"
  end: "2026-07-31"

schedule:
  interval_hours: 6

notify_on_empty: true

telegram:
  bot_token: "YOUR_BOT_TOKEN"
  chat_id: "YOUR_CHAT_ID"

playwright:
  headless: true
```

- [ ] **Step 3: Add `config.yaml` to `.gitignore`**

Append to the existing `.gitignore`:

```
config.yaml
```

- [ ] **Step 4: Write failing tests for config loader**

Create `tests/__init__.py` (empty file).

Create `tests/test_config_loader.py`:

```python
import pytest
from datetime import date
from config_loader import load_config, Config, Route

VALID_YAML = """
routes:
  - origin: CGO
    destination: JFK
    cabin: economy
dates:
  start: "2026-07-01"
  end: "2026-07-31"
schedule:
  interval_hours: 6
notify_on_empty: true
telegram:
  bot_token: "tok123"
  chat_id: "456"
playwright:
  headless: true
"""

def test_load_valid_config(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(VALID_YAML)
    config = load_config(str(cfg_file))
    assert isinstance(config, Config)
    assert len(config.routes) == 1
    assert config.routes[0] == Route(origin="CGO", destination="JFK", cabin="economy")
    assert config.date_start == date(2026, 7, 1)
    assert config.date_end == date(2026, 7, 31)
    assert config.interval_hours == 6
    assert config.notify_on_empty is True
    assert config.telegram_bot_token == "tok123"
    assert config.telegram_chat_id == "456"
    assert config.headless is True

def test_missing_config_file_exits():
    with pytest.raises(SystemExit):
        load_config("/nonexistent/config.yaml")

def test_missing_required_key_exits(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("routes: []\n")  # missing dates, schedule, telegram
    with pytest.raises(SystemExit):
        load_config(str(cfg_file))

def test_notify_on_empty_defaults_true(tmp_path):
    yaml_without_flag = VALID_YAML.replace("notify_on_empty: true\n", "")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_without_flag)
    config = load_config(str(cfg_file))
    assert config.notify_on_empty is True

def test_headless_defaults_true(tmp_path):
    yaml_without_playwright = VALID_YAML.replace("playwright:\n  headless: true\n", "")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_without_playwright)
    config = load_config(str(cfg_file))
    assert config.headless is True
```

- [ ] **Step 5: Run tests to verify they fail**

```bash
pytest tests/test_config_loader.py -v
```

Expected: `ModuleNotFoundError: No module named 'config_loader'`

- [ ] **Step 6: Implement `config_loader.py`**

```python
import yaml
from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class Route:
    origin: str
    destination: str
    cabin: str


@dataclass
class Config:
    routes: List[Route]
    date_start: date
    date_end: date
    interval_hours: int
    notify_on_empty: bool
    telegram_bot_token: str
    telegram_chat_id: str
    headless: bool


def load_config(path: str = "config.yaml") -> Config:
    try:
        with open(path) as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: config.yaml not found at '{path}'. "
                         "Copy config.yaml.example to config.yaml and fill in your values.")
    try:
        routes = [
            Route(
                origin=r["origin"],
                destination=r["destination"],
                cabin=r["cabin"],
            )
            for r in raw["routes"]
        ]
        return Config(
            routes=routes,
            date_start=date.fromisoformat(raw["dates"]["start"]),
            date_end=date.fromisoformat(raw["dates"]["end"]),
            interval_hours=int(raw["schedule"]["interval_hours"]),
            notify_on_empty=bool(raw.get("notify_on_empty", True)),
            telegram_bot_token=str(raw["telegram"]["bot_token"]),
            telegram_chat_id=str(raw["telegram"]["chat_id"]),
            headless=bool(raw.get("playwright", {}).get("headless", True)),
        )
    except (KeyError, ValueError, TypeError) as e:
        raise SystemExit(f"ERROR: Invalid config.yaml: {e}")
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
pytest tests/test_config_loader.py -v
```

Expected: 5 tests PASSED.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt config.yaml.example .gitignore config_loader.py tests/
git commit -m "feat: project scaffold and config loader"
```

---

## Task 2: Telegram notifier

**Files:**
- Create: `notifier.py`
- Create: `tests/test_notifier.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_notifier.py`:

```python
from datetime import date
from unittest.mock import patch, MagicMock
from config_loader import Config, Route
from checker import AvailableAward
import notifier


def _make_config(**overrides):
    defaults = dict(
        routes=[Route("CGO", "JFK", "economy")],
        date_start=date(2026, 7, 1),
        date_end=date(2026, 7, 31),
        interval_hours=6,
        notify_on_empty=True,
        telegram_bot_token="tok",
        telegram_chat_id="123",
        headless=True,
    )
    defaults.update(overrides)
    return Config(**defaults)


def test_send_available_posts_to_telegram():
    config = _make_config()
    award = AvailableAward(
        date=date(2026, 7, 15),
        route=Route("CGO", "JFK", "economy"),
        miles_required=35000,
    )
    with patch("notifier.requests.post") as mock_post:
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        notifier.send_available(config, award)
    mock_post.assert_called_once()
    payload = mock_post.call_args.kwargs["json"]
    assert payload["chat_id"] == "123"
    assert "CGO" in payload["text"]
    assert "JFK" in payload["text"]
    assert "35,000" in payload["text"]
    assert "2026-07-15" in payload["text"]


def test_send_empty_posts_when_notify_on_empty_true():
    config = _make_config(notify_on_empty=True)
    route = Route("CGO", "JFK", "economy")
    with patch("notifier.requests.post") as mock_post:
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        notifier.send_empty(config, route, date(2026, 7, 1), date(2026, 7, 31), 6)
    mock_post.assert_called_once()
    payload = mock_post.call_args.kwargs["json"]
    assert "CGO" in payload["text"]
    assert "JFK" in payload["text"]


def test_send_empty_skips_when_notify_on_empty_false():
    config = _make_config(notify_on_empty=False)
    route = Route("CGO", "JFK", "economy")
    with patch("notifier.requests.post") as mock_post:
        notifier.send_empty(config, route, date(2026, 7, 1), date(2026, 7, 31), 6)
    mock_post.assert_not_called()


def test_send_available_logs_error_on_failure():
    config = _make_config()
    award = AvailableAward(
        date=date(2026, 7, 15),
        route=Route("CGO", "JFK", "economy"),
        miles_required=35000,
    )
    import requests as req
    with patch("notifier.requests.post", side_effect=req.RequestException("timeout")):
        notifier.send_available(config, award)  # must not raise
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_notifier.py -v
```

Expected: `ModuleNotFoundError: No module named 'notifier'`

- [ ] **Step 3: Implement `notifier.py`**

```python
import logging
from datetime import date

import requests

from checker import AvailableAward
from config_loader import Config, Route

logger = logging.getLogger(__name__)

_TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"
_AWARD_URL = "https://www.cathaypacific.com/cx/en_US/book-a-trip/redeem-miles.html"


def send_available(config: Config, award: AvailableAward) -> None:
    miles = f"{award.miles_required:,}" if award.miles_required is not None else "unknown"
    text = (
        f"✈️ Award Space Found — {award.route.origin} → {award.route.destination}\n"
        f"\U0001f4c5 Date: {award.date.strftime('%Y-%m-%d')}\n"
        f"\U0001f4ba Cabin: {award.route.cabin.title()}\n"
        f"\U0001f3ab Miles required: {miles}\n"
        f"\U0001f517 {_AWARD_URL}"
    )
    _send(config, text)


def send_empty(config: Config, route: Route, date_start: date, date_end: date, interval_hours: int) -> None:
    if not config.notify_on_empty:
        return
    text = (
        f"No award space found for {route.origin} → {route.destination} "
        f"({date_start.strftime('%b %-d')}–{date_end.strftime('%b %-d')}). "
        f"Next check in {interval_hours} hours."
    )
    _send(config, text)


def _send(config: Config, text: str) -> None:
    url = _TELEGRAM_URL.format(token=config.telegram_bot_token)
    try:
        resp = requests.post(
            url,
            json={"chat_id": config.telegram_chat_id, "text": text},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Telegram message sent.")
    except requests.RequestException as e:
        logger.error("Telegram send failed: %s", e)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_notifier.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add notifier.py tests/test_notifier.py
git commit -m "feat: telegram notifier"
```

---

## Task 3: Award checker

**Files:**
- Create: `checker.py`
- Create: `tests/test_checker.py`

**Note on selectors:** Cathay Pacific's site uses a JavaScript SPA. The selectors in `SELECTORS` dict are best-effort guesses. Task 6 covers verifying and fixing them against the live site.

- [ ] **Step 1: Write failing tests for pure functions**

Create `tests/test_checker.py`:

```python
from datetime import date
from unittest.mock import MagicMock, patch
from config_loader import Route
from checker import _date_range, _parse_miles, AvailableAward


def test_date_range_inclusive():
    result = _date_range(date(2026, 7, 1), date(2026, 7, 3))
    assert result == [date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3)]


def test_date_range_single_day():
    result = _date_range(date(2026, 7, 1), date(2026, 7, 1))
    assert result == [date(2026, 7, 1)]


def test_parse_miles_plain_number():
    assert _parse_miles("35000 miles") == 35000


def test_parse_miles_with_comma():
    assert _parse_miles("35,000 miles") == 35000


def test_parse_miles_k_suffix():
    assert _parse_miles("35K miles") == 35000


def test_parse_miles_lowercase_k():
    assert _parse_miles("35k") == 35000


def test_parse_miles_unrecognised_returns_none():
    assert _parse_miles("Not available") is None
    assert _parse_miles("") is None


def test_check_one_returns_empty_on_timeout():
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    import checker

    mock_browser = MagicMock()
    mock_page = MagicMock()
    mock_browser.new_page.return_value = mock_page
    mock_page.goto.side_effect = PlaywrightTimeoutError("timeout")

    route = Route("CGO", "JFK", "economy")
    result = checker._check_one(mock_browser, route, date(2026, 7, 1), headless=True)
    assert result == []
    mock_page.close.assert_called_once()


def test_check_one_returns_empty_on_captcha():
    import checker

    mock_browser = MagicMock()
    mock_page = MagicMock()
    mock_browser.new_page.return_value = mock_page
    mock_page.goto.return_value = None

    # simulate captcha detected
    captcha_locator = MagicMock()
    captcha_locator.count.return_value = 1
    mock_page.locator.return_value = captcha_locator
    mock_page.wait_for_load_state.return_value = None

    route = Route("CGO", "JFK", "economy")
    with patch.object(checker, "_dismiss_cookie_banner"), \
         patch.object(checker, "_fill_search_form"), \
         patch.object(checker, "_submit_search"), \
         patch.object(checker, "_has_captcha", return_value=True):
        result = checker._check_one(mock_browser, route, date(2026, 7, 1), headless=True)

    assert result == []
    mock_page.close.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_checker.py -v
```

Expected: `ModuleNotFoundError: No module named 'checker'`

- [ ] **Step 3: Implement `checker.py`**

```python
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

# All site selectors in one place — update these after running Task 6 selector verification.
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
    # Select one-way trip
    page.locator(SELECTORS["one_way"]).first.click(timeout=8000)

    # Fill origin
    origin_input = page.locator(SELECTORS["origin_input"]).first
    origin_input.fill(route.origin)
    page.locator(SELECTORS["origin_option"].format(code=route.origin)).first.click(timeout=8000)

    # Fill destination
    dest_input = page.locator(SELECTORS["destination_input"]).first
    dest_input.fill(route.destination)
    page.locator(SELECTORS["destination_option"].format(code=route.destination)).first.click(timeout=8000)

    # Enter departure date (DD/MM/YYYY format used by CX)
    date_input = page.locator(SELECTORS["date_input"]).first
    date_input.fill(travel_date.strftime("%d/%m/%Y"))


def _submit_search(page) -> None:
    page.locator(SELECTORS["search_button"]).first.click(timeout=8000)
    page.wait_for_load_state("networkidle", timeout=30000)


def _parse_results(page, route: Route, travel_date: date) -> List[AvailableAward]:
    # Check for login wall
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
        return val if val > 100 else None  # ignore small numbers (seats count, etc.)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_checker.py -v
```

Expected: 9 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add checker.py tests/test_checker.py
git commit -m "feat: playwright award checker"
```

---

## Task 4: Scheduler and entry point

**Files:**
- Create: `scheduler.py`
- Create: `main.py`

- [ ] **Step 1: Implement `scheduler.py`**

```python
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

import checker as checker_module
import notifier as notifier_module
from config_loader import Config

logger = logging.getLogger(__name__)


def start(config: Config) -> None:
    sched = BlockingScheduler()

    def job() -> None:
        logger.info("=== Award check run starting ===")
        results = checker_module.check_all(config)

        route_hits = {}
        for award in results:
            key = (award.route.origin, award.route.destination)
            route_hits.setdefault(key, []).append(award)

        for route in config.routes:
            key = (route.origin, route.destination)
            awards = route_hits.get(key, [])
            if awards:
                for award in awards:
                    notifier_module.send_available(config, award)
            else:
                notifier_module.send_empty(config, route, config.date_start, config.date_end, config.interval_hours)

        logger.info("=== Run complete — %d award(s) found ===", len(results))

    sched.add_job(job, "interval", hours=config.interval_hours)
    job()  # immediate check on startup
    logger.info("Scheduler running. Next check in %d hour(s). Ctrl+C to stop.", config.interval_hours)
    sched.start()
```

- [ ] **Step 2: Implement `main.py`**

```python
import logging
import sys

from config_loader import load_config
from scheduler import start

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Loading configuration...")
    config = load_config("config.yaml")
    logger.info(
        "Monitoring %d route(s) from %s to %s, checking every %d hour(s).",
        len(config.routes),
        config.date_start,
        config.date_end,
        config.interval_hours,
    )
    start(config)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Smoke test — verify import chain is clean**

```bash
python -c "import main; print('imports OK')"
```

Expected output: `imports OK`

- [ ] **Step 4: Commit**

```bash
git add scheduler.py main.py
git commit -m "feat: scheduler and entry point"
```

---

## Task 5: Docker deployment files

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY *.py .

CMD ["python", "main.py"]
```

- [ ] **Step 2: Create `docker-compose.yml`**

```yaml
services:
  checker:
    build: .
    restart: unless-stopped
    volumes:
      - ./config.yaml:/app/config.yaml:ro
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

- [ ] **Step 3: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: docker deployment files"
```

---

## Task 6: Selector verification on live site

**This task is performed on your local machine with `headless: false` in `config.yaml` so you can see the browser.**

The selectors in `checker.py`'s `SELECTORS` dict are best-effort guesses. This task finds the real selectors by running against the live site.

- [ ] **Step 1: Create a local `config.yaml` from the example**

```bash
cp config.yaml.example config.yaml
```

Fill in real values: your Telegram bot token, chat_id. Set `headless: false`.

- [ ] **Step 2: Install dependencies locally**

```bash
pip install -r requirements.txt
playwright install chromium
```

- [ ] **Step 3: Run a single-date check in headed mode to observe the browser**

Create a temporary `debug_check.py`:

```python
from datetime import date
from config_loader import load_config
from checker import _check_one
from playwright.sync_api import sync_playwright

config = load_config("config.yaml")
route = config.routes[0]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    result = _check_one(browser, route, date(2026, 7, 15), headless=False)
    print("Results:", result)
    browser.close()
```

```bash
python debug_check.py
```

Watch the browser. Note where it fails (cookie banner, form fields, search button, results page).

- [ ] **Step 4: Use Playwright Inspector to find correct selectors**

Open the inspector while the script runs:

```bash
PWDEBUG=1 python debug_check.py
```

The Playwright Inspector opens alongside the browser. Click "Pick locator" and hover over each element to get the correct selector.

Find selectors for:
1. Cookie accept button
2. One-way radio/tab
3. Origin input
4. Origin autocomplete option
5. Destination input
6. Destination autocomplete option
7. Date input
8. Search button
9. Flight result cards
10. Miles price inside a card

- [ ] **Step 5: Update `SELECTORS` dict in `checker.py` with verified values**

Replace the relevant entries in the `SELECTORS` dict with what the Inspector showed. Example (your values will differ):

```python
SELECTORS = {
    "cookie_accept": '#onetrust-accept-btn-handler',
    "one_way": '[data-cy="trip-type-one-way"]',
    "origin_input": '[data-cy="origin-input"]',
    ...
}
```

- [ ] **Step 6: Re-run full check and verify Telegram notification arrives**

```bash
python main.py
```

Expected: browser opens, fills form, searches, and either a "found" or "not found" Telegram message arrives within 2 minutes.

- [ ] **Step 7: Delete `debug_check.py`, commit selector fixes**

```bash
rm debug_check.py
git add checker.py
git commit -m "fix: verified CX site selectors"
```

---

## Task 7: Deploy to Oracle Cloud

- [ ] **Step 1: Provision Oracle Cloud ARM VM**

In Oracle Cloud Console:
1. Compute → Instances → Create Instance
2. Shape: Ampere A1 Flex — 2 OCPU, 4 GB RAM
3. Image: Canonical Ubuntu 22.04
4. Add your SSH public key
5. Note the public IP

- [ ] **Step 2: SSH into the VM and install Docker**

```bash
ssh ubuntu@<YOUR_VM_IP>
```

On the VM:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker ubuntu
newgrp docker
```

- [ ] **Step 3: Clone the repo and create `config.yaml` on the VM**

```bash
git clone https://github.com/michaellifly/airline_ticket.git
cd airline_ticket
cp config.yaml.example config.yaml
nano config.yaml   # fill in real bot_token, chat_id, set headless: true
```

- [ ] **Step 4: Build and start the container**

```bash
docker compose up -d --build
```

- [ ] **Step 5: Verify it's running and check logs**

```bash
docker compose logs -f
```

Expected: Log lines showing config loaded, check run starting, Telegram message sent.

- [ ] **Step 6: Verify Telegram message received**

Check your Telegram chat. You should receive either an award found message or a "no award space found" message.

---

## Self-Review Checklist

- [x] Config loading with validation — Task 1
- [x] Telegram available notification — Task 2
- [x] Telegram empty notification with `notify_on_empty` flag — Task 2
- [x] Telegram failure does not crash — Task 2 (notifier catches RequestException)
- [x] Playwright checker per route + date — Task 3
- [x] Cookie banner handling — Task 3
- [x] CAPTCHA detection + skip — Task 3
- [x] Login wall detection + skip — Task 3
- [x] Timeout + error skip without crash — Task 3
- [x] Miles parsing (plain, comma, K suffix) — Task 3
- [x] Scheduler: immediate run + interval — Task 4
- [x] Docker ARM64 + restart policy — Task 5
- [x] Selector verification workflow — Task 6
- [x] Full deployment steps — Task 7
