import logging
import threading
import time

import requests
from apscheduler.schedulers.blocking import BlockingScheduler

import checker as checker_module
import notifier as notifier_module
from config_loader import Config

logger = logging.getLogger(__name__)

_TELEGRAM_BASE = "https://api.telegram.org/bot{token}"


def _poll_commands(config: Config, job_fn) -> None:
    base = _TELEGRAM_BASE.format(token=config.telegram_bot_token)
    offset = None
    while True:
        try:
            params = {"timeout": 30, "allowed_updates": ["message"]}
            if offset is not None:
                params["offset"] = offset
            resp = requests.get(f"{base}/getUpdates", params=params, timeout=35)
            resp.raise_for_status()
            for update in resp.json().get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "").strip()
                if chat_id != config.telegram_chat_id:
                    continue
                if text == "/check":
                    logger.info("Manual /check triggered via Telegram")
                    requests.post(f"{base}/sendMessage", json={
                        "chat_id": config.telegram_chat_id,
                        "text": "Starting manual check now...",
                    }, timeout=10)
                    threading.Thread(target=job_fn, daemon=True).start()
        except Exception as e:
            logger.warning("Command poll error: %s", e)
            time.sleep(5)


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

    threading.Thread(target=_poll_commands, args=(config, job), daemon=True).start()
    sched.add_job(job, "interval", hours=config.interval_hours)
    job()  # immediate check on startup
    logger.info("Scheduler running. Next check in %d hour(s). Ctrl+C to stop.", config.interval_hours)
    sched.start()
