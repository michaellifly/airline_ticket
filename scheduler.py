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


def _route_key(route):
    return (route.origin, route.via, route.destination, route.cabin, route.adults)


def _poll_commands(config: Config, job_fn) -> None:
    logger.info("Command polling thread started")
    base = _TELEGRAM_BASE.format(token=config.telegram_bot_token)
    offset = None
    while True:
        try:
            params = {"timeout": 20}
            if offset is not None:
                params["offset"] = offset
            resp = requests.get(f"{base}/getUpdates", params=params, timeout=25)
            resp.raise_for_status()
            updates = resp.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "").strip()
                if chat_id != config.telegram_chat_id:
                    continue
                if text.startswith("/check"):
                    logger.info("Manual /check triggered via Telegram")
                    try:
                        requests.post(f"{base}/sendMessage", json={
                            "chat_id": config.telegram_chat_id,
                            "text": "Starting manual check now...",
                        }, timeout=10)
                    except Exception:
                        pass
                    threading.Thread(target=job_fn, daemon=True).start()
        except Exception as e:
            logger.warning("Command poll error: %s — retrying in 10s", e)
            time.sleep(10)
        except BaseException as e:
            logger.error("Command poll fatal error: %s — restarting in 10s", e)
            time.sleep(10)


def _start_poll_thread(config: Config, job_fn) -> None:
    def supervised():
        while True:
            try:
                _poll_commands(config, job_fn)
            except BaseException as e:
                logger.error("Poll thread died (%s), restarting in 10s", e)
                time.sleep(10)

    t = threading.Thread(target=supervised, daemon=True, name="cmd-poll")
    t.start()
    logger.info("Polling supervisor started (thread: %s)", t.name)


def start(config: Config) -> None:
    sched = BlockingScheduler()

    def job() -> None:
        logger.info("=== Award check run starting ===")
        results = checker_module.check_all(config)

        route_hits = {}
        for award in results:
            key = _route_key(award.route)
            route_hits.setdefault(key, []).append(award)

        for route in config.routes:
            key = _route_key(route)
            awards = route_hits.get(key, [])
            if awards:
                for award in awards:
                    notifier_module.send_available(config, award)
            else:
                notifier_module.send_empty(config, route, config.date_start, config.date_end, config.interval_hours)

        logger.info("=== Run complete — %d award(s) found ===", len(results))

    _start_poll_thread(config, job)
    sched.add_job(job, "interval", hours=config.interval_hours)
    job()
    logger.info("Scheduler running. Next check in %d hour(s). Ctrl+C to stop.", config.interval_hours)
    sched.start()
