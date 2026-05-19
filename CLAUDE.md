# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Cathay Pacific award seat availability checker. Polls the CX API on a schedule and sends Telegram notifications when award seats open up.

- **Route:** CGO → HKG → JFK (two legs, connecting via Hong Kong), economy, 2 adults
- **Date range:** 2026-07-24 to 2026-08-05
- **Check interval:** every 6 hours (plus manual `/check` via Telegram bot)

## Running Tests

```bash
pytest                        # run all tests
pytest tests/test_checker.py  # run a single test file
pytest -k test_connecting     # run tests matching a name pattern
```

No build step. Dependencies: `pip install -r requirements.txt`.

## Architecture

```
main.py          → loads config, calls scheduler.start()
config_loader.py → merges config.yaml + config.secrets.yaml into Config/Route dataclasses
scheduler.py     → BlockingScheduler fires job() every N hours; also runs a daemon thread
                   that long-polls Telegram for /check commands
checker.py       → check_all() iterates routes; direct routes call API once, connecting
                   routes call API twice (one per leg) and intersect available dates
notifier.py      → send_available() or send_empty() posts to Telegram Bot API
```

**Config loading:** `config_loader.load_config()` reads `config.yaml` first, then deep-merges `config.secrets.yaml` on top. Secrets file is optional (values may be injected via the YAML directly on the VM). The merged result is validated into a `Config` dataclass.

**Connecting route date math:** Leg 2 (HKG→JFK) departs the day *after* leg 1 (CGO→HKG). `checker.py` fetches leg 2 with `date_start+1 / date_end+1`, then intersects: a departure date `d` is valid only if leg 1 has `d` available AND leg 2 has `d+1` available.

**Available seat codes:** `{"H", "L", "M"}` — any other value (e.g. `"NA"`) means no award space.

**`notify_on_empty`** (config.yaml): when `true`, sends a "no space found" message every check cycle so you know the bot is alive.

## CX API

```
https://api.cathaypacific.com/afr/search/availability/en.{origin}.{dest}.{cabin}.CX.{adults}.{start}.{end}.json
```

- Segment-based — querying CGO→JFK direct returns empty; each leg must be queried separately.
- `cabin` codes: `eco`, `bus`, `fir` (mapped from config values `economy`, `business`, `first`).
- Dates formatted `YYYYMMDD`. Response key: `data.availabilities.std[].{date, availability}`.

## Deployment

The app runs on a **GCP VM** inside Docker. Docker is not installed locally.

**Deploy:** push to `main` → GitHub Actions SCPs `*.py`, `*.yaml`, `requirements.txt`, `Dockerfile`, `docker-compose.yml` to the VM, then runs `sudo docker compose up -d --build`.

**Config on VM:** `config.yaml` and `config.secrets.yaml` are mounted read-only into `/app/`. They are *not* deployed by CI — manage them directly on the VM.

See `CLAUDE.local.md` (gitignored) for SSH details and log commands.
