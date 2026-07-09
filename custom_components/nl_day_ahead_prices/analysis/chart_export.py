"""ApexCharts-friendly price export."""

from __future__ import annotations

from ..models import PriceEntry
from ..price_resolution import convert_prices_to_resolution, infer_price_resolution


def export_prices(prices: list[PriceEntry], resolution: str = "auto") -> list[dict]:
    """Export normalized time/price objects."""
    selected = prices
    if resolution != "auto" and prices:
        selected = convert_prices_to_resolution(prices, resolution, infer_price_resolution(prices))
    return [item.as_attribute() for item in selected]


def apexcharts_yaml(entity_id: str) -> str:
    """Return a compact ApexCharts configuration using integration attributes."""
    return f"""type: custom:apexcharts-card
graph_span: 48h
span:
  start: day
yaxis:
  - decimals: 3
    min: ~0
series:
  - entity: {entity_id}
    name: Market price
    data_generator: |
      return entity.attributes.prices.map(p => [new Date(p.time).getTime(), p.price]);
  - entity: {entity_id}
    name: All-in price
    data_generator: |
      return [...entity.attributes.all_in_prices_today, ...entity.attributes.all_in_prices_tomorrow]
        .map(p => [new Date(p.time).getTime(), p.price]);
  - entity: {entity_id}
    name: Cheapest period
    type: area
    color: "#2e7d32"
    data_generator: |
      return entity.attributes.best_periods.flatMap(period =>
        period.prices.map(p => [new Date(p.time).getTime(), p.price]));
  - entity: {entity_id}
    name: Peak period
    type: area
    color: "#c62828"
    data_generator: |
      return entity.attributes.peak_periods.flatMap(period =>
        period.prices.map(p => [new Date(p.time).getTime(), p.price]));
"""
