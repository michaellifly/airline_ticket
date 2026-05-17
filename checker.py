from dataclasses import dataclass
from datetime import date
from typing import Optional
from config_loader import Route


@dataclass
class AvailableAward:
    date: date
    route: Route
    miles_required: Optional[int]
