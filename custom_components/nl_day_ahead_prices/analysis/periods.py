"""Best and peak consecutive price period detection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ..models import PriceEntry


@dataclass(frozen=True)
class PricePeriod:
    """A selected consecutive price period."""

    start: datetime
    end: datetime
    average_price: float
    entries: tuple[PriceEntry, ...]

    def contains(self, now: datetime) -> bool:
        return self.start <= now < self.end

    def as_dict(self) -> dict:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "average_price": round(self.average_price, 6),
            "prices": [item.as_attribute() for item in self.entries],
        }


def find_price_periods(
    prices: list[PriceEntry],
    duration_minutes: int,
    *,
    peak: bool = False,
    flex_percent: float = 0,
    minimum_gap_minutes: int = 0,
    allow_relaxation: bool = True,
) -> list[PricePeriod]:
    """Find non-overlapping lowest or highest windows within a flexible band."""
    candidates = _windows(prices, duration_minutes, minimum_gap_minutes if allow_relaxation else 0)
    if not candidates:
        return []
    extreme = (max if peak else min)(item.average_price for item in candidates)
    tolerance = abs(extreme) * max(0, flex_percent) / 100
    eligible = [
        item
        for item in candidates
        if (
            item.average_price >= extreme - tolerance
            if peak
            else item.average_price <= extreme + tolerance
        )
    ]
    ordered = sorted(eligible, key=lambda item: item.start)
    selected: list[PricePeriod] = []
    for candidate in ordered:
        if not selected or candidate.start >= selected[-1].end + timedelta(minutes=minimum_gap_minutes):
            selected.append(candidate)
    return selected


def active_and_next(periods: list[PricePeriod], now: datetime) -> tuple[PricePeriod | None, PricePeriod | None]:
    """Return the active period and first future period."""
    active = next((period for period in periods if period.contains(now)), None)
    upcoming = next((period for period in periods if period.start > now), None)
    return active, upcoming


def _windows(prices: list[PriceEntry], duration_minutes: int, gap_minutes: int) -> list[PricePeriod]:
    if duration_minutes <= 0:
        return []
    ordered = sorted(prices, key=lambda item: item.time)
    default = _default_interval(ordered)
    target = timedelta(minutes=duration_minutes)
    allowed_gap = timedelta(minutes=max(0, gap_minutes))
    result: list[PricePeriod] = []
    for start in range(len(ordered)):
        entries: list[PriceEntry] = []
        elapsed = timedelta()
        cursor = ordered[start].time
        for index in range(start, len(ordered)):
            item = ordered[index]
            gap = item.time - cursor
            if gap > allowed_gap:
                break
            duration = _duration(ordered, index, default)
            if elapsed + gap + duration > target:
                break
            entries.append(item)
            elapsed += gap + duration
            cursor = item.time + duration
            if elapsed == target:
                result.append(
                    PricePeriod(entries[0].time, entries[0].time + target, sum(x.price for x in entries) / len(entries), tuple(entries))
                )
                break
    return result


def _default_interval(prices: list[PriceEntry]) -> timedelta:
    deltas = [
        b.time - a.time
        for a, b in zip(prices, prices[1:])  # noqa: B905 - Python 3.9 compatibility.
        if b.time > a.time
    ]
    return min(deltas, default=timedelta(hours=1))


def _duration(prices: list[PriceEntry], index: int, default: timedelta) -> timedelta:
    if index + 1 < len(prices):
        delta = prices[index + 1].time - prices[index].time
        if timedelta() < delta <= timedelta(hours=1):
            return delta
    return default
