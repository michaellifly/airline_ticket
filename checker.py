import logging
import requests
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

from config_loader import Config, Route

logger = logging.getLogger(__name__)

AVAILABLE_CODES = {"H", "L", "M"}

API_URL = "https://api.cathaypacific.com/afr/search/availability/en.{origin}.{dest}.{cabin}.CX.{adults}.{start}.{end}.json"

CABIN_MAP = {"economy": "eco", "business": "bus", "first": "fir"}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://book.cathaypacific.com/",
    "Origin": "https://book.cathaypacific.com",
}


@dataclass
class AvailableAward:
    date: date
    route: Route
    miles_required: Optional[int]


def check_all(config: Config) -> List[AvailableAward]:
    results = []
    for route in config.routes:
        awards = _check_route(route, config.date_start, config.date_end)
        results.extend(awards)
    return results


def _check_route(route: Route, date_start: date, date_end: date) -> List[AvailableAward]:
    if route.via:
        return _check_connecting_route(route, date_start, date_end)
    return _check_direct_route(route, date_start, date_end)


def _check_direct_route(route: Route, date_start: date, date_end: date) -> List[AvailableAward]:
    label = f"{route.origin}->{route.destination}"
    logger.info("Checking %s (%s to %s)", label, date_start, date_end)
    available_dates = _fetch_available_dates(route.origin, route.destination, route.cabin, route.adults, date_start, date_end)
    if available_dates is None:
        return []
    results = [AvailableAward(date=d, route=route, miles_required=None) for d in sorted(available_dates)]
    logger.info("Found %d available date(s) for %s", len(results), label)
    return results


def _check_connecting_route(route: Route, date_start: date, date_end: date) -> List[AvailableAward]:
    label = f"{route.origin}->{route.via}->{route.destination}"
    logger.info("Checking %s (%s to %s)", label, date_start, date_end)

    # Leg 1: origin → via, departing on the user's requested date
    leg1_dates = _fetch_available_dates(route.origin, route.via, route.cabin, route.adults, date_start, date_end)
    if leg1_dates is None:
        return []

    # Leg 2: via → destination, departing the day AFTER leg 1
    # (e.g. CGO departs Jul 25 afternoon, arrives HKG same evening,
    #  HKG→JFK departs Jul 26 — so leg 2 date = leg 1 date + 1)
    leg2_start = date_start + timedelta(days=1)
    leg2_end = date_end + timedelta(days=1)
    leg2_dates = _fetch_available_dates(route.via, route.destination, route.cabin, route.adults, leg2_start, leg2_end)
    if leg2_dates is None:
        return []

    # A journey departing origin on date d requires via→dest available on d+1
    both_available = sorted(d for d in leg1_dates if d + timedelta(days=1) in leg2_dates)
    results = [AvailableAward(date=d, route=route, miles_required=None) for d in both_available]
    logger.info("Found %d date(s) with both legs available for %s", len(results), label)
    return results


def _fetch_available_dates(origin: str, destination: str, cabin: str, adults: int,
                           date_start: date, date_end: date) -> Optional[set]:
    cabin_code = CABIN_MAP.get(cabin.lower(), "eco")
    url = API_URL.format(
        origin=origin,
        dest=destination,
        cabin=cabin_code,
        adults=adults,
        start=date_start.strftime("%Y%m%d"),
        end=date_end.strftime("%Y%m%d"),
    )
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout:
        logger.warning("Timeout fetching %s->%s", origin, destination)
        return None
    except Exception as e:
        logger.error("Error fetching %s->%s: %s", origin, destination, e)
        return None

    available = set()
    for entry in data.get("availabilities", {}).get("std", []):
        if entry.get("availability") in AVAILABLE_CODES:
            try:
                d = date(int(entry["date"][:4]), int(entry["date"][4:6]), int(entry["date"][6:]))
                available.add(d)
            except Exception:
                continue
    return available
