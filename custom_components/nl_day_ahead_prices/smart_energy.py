"""Generic smart-energy and heat-source advice for EnerPrice."""

from __future__ import annotations

from datetime import datetime
from typing import Any

DEFAULT_GAS_KWH_PER_M3 = 9.769


def build_smart_energy_advice(
    *,
    electricity_price: float | None,
    future_prices: list[Any] | None = None,
    now: datetime | None = None,
    solar_power_w: float | None = None,
    grid_power_w: float | None = None,
    gas_price_per_m3: float | None = None,
    electric_efficiency: float = 1.0,
    gas_efficiency: float = 0.90,
    gas_kwh_per_m3: float = DEFAULT_GAS_KWH_PER_M3,
    solar_surplus_threshold_w: float = 500.0,
    language: str = "en",
) -> dict[str, Any]:
    """Compare solar, grid electricity, gas and waiting for flexible heat loads."""
    if electric_efficiency <= 0 or gas_efficiency <= 0 or gas_kwh_per_m3 <= 0:
        raise ValueError("Efficiencies and gas energy content must be positive")

    is_nl = language.lower().startswith("nl")
    solar = solar_power_w if solar_power_w is not None else 0.0
    grid = grid_power_w if grid_power_w is not None else 0.0
    solar_production = solar > 0
    # Positive grid power means import. When grid data is available, actual export is
    # the most reliable definition of surplus. Solar production alone is used only
    # when no grid meter was supplied.
    measured_surplus = max(0.0, -grid) if grid_power_w is not None else None
    solar_surplus = (
        measured_surplus >= solar_surplus_threshold_w
        if measured_surplus is not None
        else solar >= solar_surplus_threshold_w
    )

    electric_heat_cost = (
        electricity_price / electric_efficiency if electricity_price is not None else None
    )
    gas_heat_cost = (
        gas_price_per_m3 / (gas_kwh_per_m3 * gas_efficiency)
        if gas_price_per_m3 is not None
        else None
    )
    timing = _future_context(electricity_price, future_prices or [], now, electric_efficiency)

    if solar_surplus:
        state = "solar_surplus"
        recommendation = (
            "Gebruik eigen zonnestroom voor flexibel elektrisch verwarmen."
            if is_nl else
            "Use available solar surplus for flexible electric heating."
        )
    elif electric_heat_cost is not None and gas_heat_cost is not None:
        if timing["future_electric_heat_cost"] is not None and timing["future_electric_heat_cost"] < min(
            electric_heat_cost, gas_heat_cost
        ) * 0.95:
            state = "wait"
            recommendation = (
                f"Wacht indien mogelijk ongeveer {timing['minutes_until_better']} min; elektrisch verwarmen wordt dan naar verwachting goedkoper dan nu."
                if is_nl else
                f"Wait about {timing['minutes_until_better']} min if practical; electric heating is expected to be cheaper then."
            )
        elif electric_heat_cost <= gas_heat_cost:
            state = "cheap_grid"
            recommendation = (
                "Elektrisch verwarmen vanaf het net is nu goedkoper dan verwarmen met gas."
                if is_nl else
                "Grid-electric heating is currently cheaper than gas heating."
            )
        else:
            state = "gas"
            recommendation = (
                "Verwarmen met gas is nu goedkoper dan elektrisch verwarmen vanaf het net."
                if is_nl else
                "Gas heating is currently cheaper than grid-electric heating."
            )
    elif electric_heat_cost is not None:
        state = "cheap_grid" if timing["next_better_price"] is None else "wait"
        recommendation = (
            "Elektriciteitsadvies beschikbaar; configureer een gasprijssensor voor een warmtebronvergelijking."
            if is_nl else
            "Electricity advice is available; configure a gas-price sensor for heat-source comparison."
        )
    else:
        state = "normal"
        recommendation = (
            "Onvoldoende gegevens voor een warmtebronadvies."
            if is_nl else
            "Not enough data is available for heat-source advice."
        )

    savings = None
    if electric_heat_cost is not None and gas_heat_cost is not None and max(electric_heat_cost, gas_heat_cost) > 0:
        savings = abs(electric_heat_cost - gas_heat_cost) / max(electric_heat_cost, gas_heat_cost) * 100

    return {
        "state": state,
        "recommendation": recommendation,
        "electricity_price": electricity_price,
        "gas_price_per_m3": gas_price_per_m3,
        "electric_heat_cost_per_kwh": _round(electric_heat_cost),
        "gas_heat_cost_per_kwh": _round(gas_heat_cost),
        "cheapest_now": (
            "electricity" if electric_heat_cost is not None and gas_heat_cost is not None and electric_heat_cost <= gas_heat_cost
            else "gas" if electric_heat_cost is not None and gas_heat_cost is not None
            else None
        ),
        "cost_difference_percent": round(savings, 1) if savings is not None else None,
        "solar_power_w": solar_power_w,
        "grid_power_w": grid_power_w,
        "solar_production": solar_production,
        "measured_solar_surplus_w": _round(measured_surplus),
        "solar_surplus": solar_surplus,
        "solar_surplus_threshold_w": solar_surplus_threshold_w,
        "electric_efficiency": electric_efficiency,
        "gas_efficiency": gas_efficiency,
        "gas_kwh_per_m3": gas_kwh_per_m3,
        **timing,
    }


def _future_context(
    current_price: float | None,
    prices: list[Any],
    now: datetime | None,
    electric_efficiency: float,
) -> dict[str, Any]:
    if current_price is None or not prices or now is None:
        return _empty_future()
    future = sorted((item for item in prices if item.time > now), key=lambda item: item.time)
    if not future:
        return _empty_future()
    threshold = current_price * 0.95 if current_price > 0 else current_price - 0.005
    better = next((item for item in future if item.price <= threshold), None)
    if better is None:
        return _empty_future()
    return {
        "next_better_time": better.time,
        "next_better_price": better.price,
        "minutes_until_better": max(0, round((better.time - now).total_seconds() / 60)),
        "future_electric_heat_cost": _round(better.price / electric_efficiency),
    }


def _empty_future() -> dict[str, Any]:
    return {
        "next_better_time": None,
        "next_better_price": None,
        "minutes_until_better": None,
        "future_electric_heat_cost": None,
    }


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None
