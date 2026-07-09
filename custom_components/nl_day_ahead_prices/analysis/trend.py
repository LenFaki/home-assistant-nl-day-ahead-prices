"""Price trend analysis."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from ..models import PriceEntry


def trend_for_prices(
    prices: list[PriceEntry],
    now: datetime,
    stable_threshold: float = 2.0,
    strong_threshold: float = 10.0,
) -> dict[str, Any]:
    """Compare current and next interval and describe the price direction."""
    ordered = sorted(prices, key=lambda item: item.time)
    current_index = next(
        (index for index, item in enumerate(ordered) if item.time <= now < _end(ordered, index)),
        None,
    )
    if current_index is None or current_index + 1 >= len(ordered):
        return {"trend": "stable", "trend_value_percent": 0.0, "next_change_time": None, "trajectory": "stable"}
    current = ordered[current_index].price
    following = ordered[current_index + 1].price
    denominator = max(abs(current), 0.000001)
    value = (following - current) / denominator * 100
    trend = classify_trend(value, stable_threshold, strong_threshold)
    change_time = None
    for index in range(current_index + 1, len(ordered) - 1):
        candidate = (ordered[index + 1].price - ordered[index].price) / max(abs(ordered[index].price), 0.000001) * 100
        if classify_trend(candidate, stable_threshold, strong_threshold) != trend:
            change_time = ordered[index + 1].time
            break
    horizon = ordered[current_index + 1 : current_index + 9]
    midpoint = max(1, len(horizon) // 2)
    first = _average(horizon[:midpoint])
    second = _average(horizon[midpoint:])
    trajectory_value = 0.0 if first is None or second is None else (second - first) / max(abs(first), 0.000001) * 100
    return {
        "trend": trend,
        "trend_value_percent": round(value, 2),
        "next_change_time": change_time,
        "trajectory": classify_trend(trajectory_value, stable_threshold, strong_threshold),
    }


def classify_trend(value: float, stable_threshold: float, strong_threshold: float) -> str:
    """Classify a percentage change."""
    if value <= -strong_threshold:
        return "strongly_falling"
    if value < -stable_threshold:
        return "falling"
    if value >= strong_threshold:
        return "strongly_rising"
    if value > stable_threshold:
        return "rising"
    return "stable"


def _end(prices: list[PriceEntry], index: int) -> datetime:
    if index + 1 < len(prices):
        return prices[index + 1].time
    return prices[index].time + timedelta(hours=1)


def _average(prices: list[PriceEntry]) -> float | None:
    return sum(item.price for item in prices) / len(prices) if prices else None
