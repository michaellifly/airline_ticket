import yaml
from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class Route:
    origin: str
    destination: str
    cabin: str


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


def load_config(path: str = "config.yaml") -> Config:
    try:
        with open(path) as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: config.yaml not found at '{path}'. "
                         "Copy config.yaml.example to config.yaml and fill in your values.")
    try:
        routes = [
            Route(
                origin=r["origin"],
                destination=r["destination"],
                cabin=r["cabin"],
            )
            for r in raw["routes"]
        ]
        return Config(
            routes=routes,
            date_start=date.fromisoformat(raw["dates"]["start"]),
            date_end=date.fromisoformat(raw["dates"]["end"]),
            interval_hours=int(raw["schedule"]["interval_hours"]),
            notify_on_empty=bool(raw.get("notify_on_empty", True)),
            telegram_bot_token=str(raw["telegram"]["bot_token"]),
            telegram_chat_id=str(raw["telegram"]["chat_id"]),
            headless=bool(raw.get("playwright", {}).get("headless", True)),
        )
    except (KeyError, ValueError, TypeError) as e:
        raise SystemExit(f"ERROR: Invalid config.yaml: {e}")
