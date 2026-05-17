# Cathay Pacific Miles Ticket Availability Checker — Design Spec

**Date:** 2026-05-17  
**Status:** Approved

---

## Overview

A scheduled Python service that automatically checks Cathay Pacific's website for award (miles) ticket availability on configured routes and date ranges, and sends Telegram notifications when seats are found.

---

## Goals

- Monitor Cathay Pacific award space for configured routes without manual checking
- Notify via Telegram when economy award seats become available
- Allow routes, date ranges, and schedule interval to be configured via a single YAML file
- Run unattended on a cloud server (Oracle Cloud Free Tier ARM VM)

---

## Non-Goals

- No web UI — configuration is file-based only
- No support for paid ticket searches — award miles only
- No multi-airline support in this version — Cathay Pacific only

---

## Configuration (`config.yaml`)

Lives on the server only — excluded from git via `.gitignore`.

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

notify_on_empty: true   # set false to silence no-availability messages

telegram:
  bot_token: "YOUR_BOT_TOKEN"
  chat_id: "YOUR_CHAT_ID"

playwright:
  headless: true
```

---

## Project Structure

```
airline_ticket/
├── Dockerfile
├── docker-compose.yml
├── config.yaml              # server-only, gitignored
├── main.py                  # entry point
├── checker.py               # Playwright award search logic
├── notifier.py              # Telegram bot notifications
├── scheduler.py             # APScheduler setup
└── requirements.txt
```

---

## Components

### `checker.py` — Award Availability Checker

Uses Playwright (headless Chromium) to automate Cathay Pacific's award search page.

**Per route + date:**
1. Navigate to Cathay Pacific award search (`https://www.cathaypacific.com`)
2. Fill in origin, destination, travel date, cabin class (Economy)
3. Submit search and wait for results
4. Scrape results — collect dates showing a miles price (not "unavailable")
5. Return list of `(date, miles_required)` tuples

**Robustness:**
- Handles cookie consent popups automatically
- On CAPTCHA or login wall: log warning, skip run, do not crash
- On page load timeout or network error: log error, skip run, scheduler continues

Iterates all dates in the configured range for each route before notifying.

---

### `notifier.py` — Telegram Notifier

Uses `python-telegram-bot` library.

**When award space is found:**
```
✈️ Award Space Found — CGO → JFK
📅 Date: 2026-07-15
💺 Cabin: Economy
🎫 Miles required: 35,000
🔗 https://www.cathaypacific.com/cx/en_US/book-a-trip/redeem-miles.html
```

One message per available date found.

**When no availability (if `notify_on_empty: true`):**
```
No award space found for CGO → JFK (Jul 1–31). Next check in 6 hours.
```

On Telegram send failure: log error, do not crash.

---

### `scheduler.py` — Scheduler

Uses APScheduler `BlockingScheduler`.

- Runs one immediate check on startup
- Repeats every `interval_hours` as configured
- Clean shutdown on `Ctrl+C`

---

### `main.py` — Entry Point

1. Load and validate `config.yaml`
2. Initialize notifier and checker with config
3. Start scheduler

Logs all activity to stdout with timestamps (captured by Docker).

---

## Deployment

**Server:** Oracle Cloud Free Tier — 1x Ampere A1 ARM VM, Ubuntu 22.04, 2 OCPU + 4GB RAM.

**Container:** Docker + Docker Compose.

```yaml
# docker-compose.yml (outline)
services:
  checker:
    build: .
    restart: unless-stopped
    volumes:
      - ./config.yaml:/app/config.yaml
```

`config.yaml` is bind-mounted from the host so it can be edited without rebuilding the image.

**Deployment workflow:**
```bash
git pull
docker compose up -d --build
docker compose logs -f
```

**Auto-restart:** `restart: unless-stopped` ensures the container restarts on VM reboot.

---

## Error Handling Summary

| Scenario | Behavior |
|---|---|
| Page load timeout | Log warning, skip run |
| CAPTCHA encountered | Log warning, skip run |
| Telegram send failure | Log error, continue |
| `config.yaml` missing | Crash with clear error message on startup |
| Invalid config values | Crash with clear error message on startup |

---

## Dependencies

```
playwright
python-telegram-bot
apscheduler
pyyaml
```

---

## Out of Scope (Future)

- Login-required award searches (member fares)
- Multiple cabin classes per route
- Price trend tracking / history
- Web UI for configuration
