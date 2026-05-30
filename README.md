# Cathay Pacific Award Checker

Monitors Cathay Pacific award seat availability and sends Telegram notifications when seats open up. Supports connecting routes (e.g. CGO → HKG → JFK) and runs on a schedule in Docker.

## Features

- Checks award availability via the Cathay Pacific API (no browser needed)
- Supports connecting routes — checks both legs and returns dates where both are available
- Sends Telegram notifications with direct booking links per available date
- Manual `/check` trigger via Telegram
- Runs on a 6-hour schedule; auto-restarts on failure
- Deploys automatically to a GCP VM on every push to `main`

## Project Structure

```
├── main.py              # Entry point
├── scheduler.py         # APScheduler loop + Telegram /check command polling
├── checker.py           # Cathay Pacific API availability logic
├── notifier.py          # Telegram message formatting and sending
├── config_loader.py     # Loads and merges config.yaml + config.secrets.yaml
├── config.yaml          # Non-sensitive config (routes, dates, schedule)
├── config.secrets.yaml  # Sensitive credentials — gitignored, never committed
├── Dockerfile
├── docker-compose.yml
└── tests/
```

## Configuration

**`config.yaml`** — committed to git, deployed automatically:

```yaml
routes:
  - origin: CGO
    destination: JFK
    via: HKG       # optional connecting airport
    cabin: economy # economy | business | first
    adults: 2
  - origin: CAN
    destination: JFK
    via: HKG
    cabin: economy
    adults: 2

dates:
  start: "2026-07-01"
  end: "2026-07-31"

schedule:
  interval_hours: 6

notify_on_empty: true   # send a message when no seats found

playwright:
  headless: true
```

Add one `routes:` item for each origin/via/destination combination you want to monitor. `via` is optional; omit it for direct flights.

**`config.secrets.yaml`** — never committed, copy from example and fill in:

```bash
cp config.secrets.yaml.example config.secrets.yaml
```

```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"   # from @BotFather
  chat_id: "YOUR_CHAT_ID"       # your Telegram user ID

cathay:
  phone: "+1XXXXXXXXXX"         # optional
  password: "YOUR_PASSWORD"     # optional
```

To get your Telegram chat ID, send any message to your bot then open:
`https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`

## Running Locally

```bash
pip install -r requirements.txt
python main.py
```

## Running with Docker

```bash
docker compose up -d --build
docker logs -f airline_ticket-checker-1
```

## Deployment (GCP)

CI/CD is configured via GitHub Actions (`.github/workflows/deploy.yml`). Every push to `main` automatically:
1. Copies code files to the GCP VM
2. Rebuilds and restarts the Docker container

`config.secrets.yaml` is **never deployed by CI/CD** — it lives on the VM permanently. To update it manually:

```bash
gcloud compute scp config.secrets.yaml USER@VM:/path/to/airline_ticket/config.secrets.yaml --zone=ZONE
gcloud compute ssh USER@VM --zone=ZONE --command="sudo docker compose -f /path/to/airline_ticket/docker-compose.yml restart"
```

Required GitHub secrets: `VM_HOST`, `VM_USER`, `VM_SSH_KEY`.

## Telegram Commands

| Command | Action |
|---------|--------|
| `/check` | Trigger an immediate availability check |

## How It Works

1. Calls `https://api.cathaypacific.com/afr/search/availability/...` for each route leg
2. For connecting routes, takes the intersection of dates where both legs have availability (`H`/`L`/`M` codes)
3. Sends one Telegram message per available date with a booking link to the Cathay Pacific award search page

## Tests

```bash
pytest tests/
```
