"""Resolution-independent price forecasts."""

from __future__ import annotations

from datetime import datetime, timedelta

from ..models import PriceEntry


def average_next_period(prices: list[PriceEntry], now: datetime, hours: int) -> float | None:
    """Return the time-weighted average from now until the requested horizon."""
    if hours <= 0:
        raise ValueError("hours must be positive")
    ordered = sorted(prices, key=lambda item: item.time)
    end = now + timedelta(hours=hours)
    weighted_total = 0.0
    covered_seconds = 0.0
    for index, entry in enumerate(ordered):
        interval_end = ordered[index + 1].time if index + 1 < len(ordered) else entry.time + _interval(ordered)
        overlap_start = max(now, entry.time)
        overlap_end = min(end, interval_end)
        seconds = max(0.0, (overlap_end - overlap_start).total_seconds())
        weighted_total += entry.price * seconds
        covered_seconds += seconds
    return weighted_total / covered_seconds if covered_seconds else None


def _interval(prices: list[PriceEntry]) -> timedelta:
    deltas = [
        b.time - a.time
        for a, b in zip(prices, prices[1:])  # noqa: B905 - Python 3.9 compatibility.
        if b.time > a.time
    ]
    return min(deltas, default=timedelta(hours=1))
