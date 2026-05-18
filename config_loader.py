import yaml
from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class Route:
    origin: str
    destination: str
    cabin: str
    via: Optional[str] = None
    adults: int = 1


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
    cathay_phone: Optional[str] = None
    cathay_password: Optional[str] = None


def load_config(path: str = "config.yaml") -> Config:
    try:
        with open(path) as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: config.yaml not found at '{path}'.")

    secrets_path = path.replace("config.yaml", "config.secrets.yaml")
    try:
        with open(secrets_path) as f:
            secrets = yaml.safe_load(f) or {}
        raw = {**raw, **{k: v for k, v in secrets.items() if v is not None}}
    except FileNotFoundError:
        pass  # secrets file is optional; values may already be in main config

    if raw is None:
        raise SystemExit(f"ERROR: config.yaml at '{path}' is empty.")

    try:
        routes = [
            Route(
                origin=r["origin"],
                destination=r["destination"],
                cabin=r["cabin"],
                via=r.get("via"),
                adults=int(r.get("adults", 1)),
            )
            for r in raw["routes"]
        ]
        date_start = date.fromisoformat(raw["dates"]["start"])
        date_end = date.fromisoformat(raw["dates"]["end"])

        if date_end < date_start:
            raise SystemExit(
                f"ERROR: dates.end ({date_end}) must not be before dates.start ({date_start})."
            )

        interval_hours = int(raw["schedule"]["interval_hours"])

        if interval_hours <= 0:
            raise SystemExit("ERROR: schedule.interval_hours must be a positive integer.")

        cathay = raw.get("cathay") or {}
        return Config(
            routes=routes,
            date_start=date_start,
            date_end=date_end,
            interval_hours=interval_hours,
            notify_on_empty=bool(raw.get("notify_on_empty", True)),
            telegram_bot_token=str(raw["telegram"]["bot_token"]),
            telegram_chat_id=str(raw["telegram"]["chat_id"]),
            headless=bool(raw.get("playwright", {}).get("headless", True)),
            cathay_phone=str(cathay["phone"]) if cathay.get("phone") else None,
            cathay_password=str(cathay["password"]) if cathay.get("password") else None,
        )
    except (KeyError, ValueError, TypeError) as e:
        raise SystemExit(f"ERROR: Invalid config.yaml: {e}")
