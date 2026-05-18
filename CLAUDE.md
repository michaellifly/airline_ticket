# Airline Ticket Checker — Project Context

## What This Project Does

Cathay Pacific award seat availability checker. Polls the CX API on a schedule and sends Telegram notifications when award seats open up.

- **Route:** CGO → HKG → JFK (two legs, connecting via Hong Kong), economy, 2 adults
- **Date range:** 2026-07-24 to 2026-08-05
- **Check interval:** every 6 hours (plus manual `/check` via Telegram bot)

## Architecture

- `main.py` — entry point, loads config, starts scheduler
- `scheduler.py` — APScheduler, fires immediately on startup then every 6 hours
- `checker.py` — calls CX API per leg, intersects available dates across legs
- `notifier.py` — sends Telegram messages on hits
- `config.yaml` — public config (route, dates, interval)
- `config.secrets.yaml` — gitignored secrets (Telegram token, chat ID)

## CX API Behavior

The API is **segment-based** — querying CGO→JFK direct returns empty. Each leg must be queried separately (CGO→HKG, then HKG→JFK). The `via` field must be set manually per leg.

## Deployment

The app runs on a **GCP VM**, not locally. Docker is not installed on the local Windows machine.

**Deployment is automatic** — pushing to `main` triggers GitHub Actions (`.github/workflows/deploy.yml`), which SCP's the files to the VM and runs `sudo docker compose up -d --build`.

See `CLAUDE.local.md` (gitignored) for SSH connection details.
