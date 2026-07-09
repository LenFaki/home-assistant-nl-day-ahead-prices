"""Price volatility statistics."""

from __future__ import annotations

from statistics import median
from typing import Any

from ..models import PriceEntry


def volatility(prices: list[PriceEntry]) -> dict[str, Any]:
    """Return descriptive statistics and a relative volatility class."""
    if not prices:
        return {"level": None}
    values = [item.price for item in prices]
    average = sum(values) / len(values)
    span = max(values) - min(values)
    percent = span / max(abs(average), 0.000001) * 100
    level = "low" if percent < 25 else "moderate" if percent < 50 else "high" if percent < 100 else "very_high"
    return {
        "level": level,
        "min_price": round(min(values), 6),
        "max_price": round(max(values), 6),
        "average_price": round(average, 6),
        "median_price": round(median(values), 6),
        "price_span": round(span, 6),
        "volatility_percent": round(percent, 2),
    }
