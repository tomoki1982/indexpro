from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class RawPage:
    manufacturer_name: str
    url: str
    title: str
    body: str
    domain: str
    fetched_at: datetime
