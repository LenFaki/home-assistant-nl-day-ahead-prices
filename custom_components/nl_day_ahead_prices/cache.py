"""Pure cache validation helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def cache_is_valid(cached: dict[str, Any] | None, now: datetime) -> bool:
    """Accept only same-local-day caches that contain today's prices."""
    if not cached or cached.get("local_date") != now.date().isoformat():
        return False
    prices_today = cached.get("prices_today")
    return isinstance(prices_today, list) and bool(prices_today)
