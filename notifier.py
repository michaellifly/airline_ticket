import html
import logging
from datetime import date

import requests

from checker import AvailableAward
from config_loader import Config, Route

logger = logging.getLogger(__name__)

_TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"

_CABIN_CLASS = {"economy": "Y", "business": "C", "first": "F"}

_BOOKING_URL_TPL = (
    "https://api.cathaypacific.com/redibe/IBEFacade"
    "?ACTION=RED_AWARD_SEARCH"
    "&ORIGIN%5B1%5D={origin}"
    "&DESTINATION%5B1%5D={dest}"
    "&DEPARTUREDATE%5B1%5D={date}"
    "&ENTRYPOINT=https%3A%2F%2Fwww.cathaypacific.com%2Fcx%2Fen_US.html"
    "&ENTRYLANGUAGE=en&ENTRYCOUNTRY=US"
    "&RETURNURL=https%3A%2F%2Fwww.cathaypacific.com%2Fcx%2Fen_US.html"
    "&ERRORURL=https%3A%2F%2Fwww.cathaypacific.com%2Fcx%2Fen_US.handler.html"
    "&LOGINURL=https%3A%2F%2Fwww.cathaypacific.com%2Fcx%2Fen_US%2Fsign-in.html"
    "&CABINCLASS={cabin}&ADULT=1&CHILD=0&DISCOUNTCODE=&FLEXIBLEDATE=false&BRAND=CX"
)


def _booking_url(award: AvailableAward) -> str:
    return _BOOKING_URL_TPL.format(
        origin=award.route.origin,
        dest=award.route.destination,
        date=award.date.strftime("%Y%m%d"),
        cabin=_CABIN_CLASS.get(award.route.cabin.lower(), "Y"),
    )


def send_available(config: Config, award: AvailableAward) -> None:
    route = award.route
    via = f" via {route.via}" if route.via else ""
    miles = f"{award.miles_required:,}" if award.miles_required is not None else "check site"
    link_label = (
        f"Book {route.origin}{via} → {route.destination} "
        f"· {award.date.strftime('%b %d')} ({route.cabin.title()})"
    )
    text = (
        f"<b>Award Space Found</b> — "
        f"{html.escape(route.origin)}{html.escape(via)} → {html.escape(route.destination)}\n"
        f"Date: {award.date.strftime('%Y-%m-%d (%A)')}\n"
        f"Cabin: {route.cabin.title()}\n"
        f"Miles: {miles}\n"
        f'<a href="{_booking_url(award)}">{html.escape(link_label)}</a>'
    )
    _send(config, text, parse_mode="HTML")


def send_empty(config: Config, route: Route, date_start: date, date_end: date, interval_hours: int) -> None:
    if not config.notify_on_empty:
        return
    start_str = date_start.strftime('%b %d').lstrip('0').replace(' 0', ' ')
    end_str = date_end.strftime('%b %d').lstrip('0').replace(' 0', ' ')
    via = f" via {route.via}" if route.via else ""
    text = (
        f"No award space found for {route.origin}{via} → {route.destination} "
        f"({start_str}–{end_str}). "
        f"Next check in {interval_hours} hours."
    )
    _send(config, text)


def _send(config: Config, text: str, parse_mode: str = "") -> None:
    url = _TELEGRAM_URL.format(token=config.telegram_bot_token)
    payload: dict = {"chat_id": config.telegram_chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Telegram message sent.")
    except requests.HTTPError as e:
        logger.error("Telegram send failed: HTTP %s", e.response.status_code)
    except requests.RequestException as e:
        logger.error("Telegram send failed: %s", type(e).__name__)
