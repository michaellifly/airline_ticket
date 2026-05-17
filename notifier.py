import logging
from datetime import date

import requests

from checker import AvailableAward
from config_loader import Config, Route

logger = logging.getLogger(__name__)

_TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"
_AWARD_URL = "https://www.cathaypacific.com/cx/en_US.html"


def send_available(config: Config, award: AvailableAward) -> None:
    route = award.route
    via = f" via {route.via}" if route.via else ""
    miles = f"{award.miles_required:,}" if award.miles_required is not None else "check site"
    text = (
        f"Award Space Found - {route.origin}{via} -> {route.destination}\n"
        f"Date: {award.date.strftime('%Y-%m-%d')}\n"
        f"Cabin: {route.cabin.title()}\n"
        f"Miles: {miles}\n"
        f"{_AWARD_URL}"
    )
    _send(config, text)


def send_empty(config: Config, route: Route, date_start: date, date_end: date, interval_hours: int) -> None:
    if not config.notify_on_empty:
        return
    start_str = date_start.strftime('%b %d').lstrip('0').replace(' 0', ' ')
    end_str = date_end.strftime('%b %d').lstrip('0').replace(' 0', ' ')
    text = (
        f"No award space found for {route.origin} → {route.destination} "
        f"({start_str}–{end_str}). "
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
    except requests.HTTPError as e:
        logger.error("Telegram send failed: HTTP %s", e.response.status_code)
    except requests.RequestException as e:
        logger.error("Telegram send failed: %s", type(e).__name__)
