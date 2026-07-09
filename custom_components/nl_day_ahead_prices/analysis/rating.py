"""Relative price ratings."""

from __future__ import annotations

from ..models import PriceEntry


def price_ratings(value: float | None, prices: list[PriceEntry]) -> tuple[str | None, str | None]:
    """Return three-level and five-level percentile ratings."""
    if value is None or not prices:
        return None, None
    values = sorted(item.price for item in prices)
    percentile = sum(item <= value for item in values) / len(values)
    rating_3 = "low" if percentile <= 1 / 3 else "high" if percentile > 2 / 3 else "normal"
    if percentile <= 0.2:
        rating_5 = "very_cheap"
    elif percentile <= 0.4:
        rating_5 = "cheap"
    elif percentile <= 0.6:
        rating_5 = "normal"
    elif percentile <= 0.8:
        rating_5 = "expensive"
    else:
        rating_5 = "very_expensive"
    return rating_3, rating_5
