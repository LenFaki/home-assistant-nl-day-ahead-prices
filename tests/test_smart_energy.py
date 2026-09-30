from datetime import datetime, timedelta, timezone

from custom_components.nl_day_ahead_prices.models import PriceEntry
from custom_components.nl_day_ahead_prices.smart_energy import build_smart_energy_advice

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)


def test_prefers_solar_surplus():
    result = build_smart_energy_advice(
        electricity_price=0.25,
        gas_price_per_m3=1.30,
        solar_power_w=2400,
        grid_power_w=-900,
        now=NOW,
    )
    assert result["state"] == "solar_surplus"
    assert result["solar_surplus"] is True


def test_compares_useful_heat_costs():
    result = build_smart_energy_advice(
        electricity_price=0.18,
        gas_price_per_m3=1.40,
        electric_efficiency=1.0,
        gas_efficiency=0.90,
        now=NOW,
    )
    assert result["state"] == "cheap_grid"
    assert result["electric_heat_cost_per_kwh"] == 0.18
    assert result["gas_heat_cost_per_kwh"] > 0.15


def test_prefers_gas_when_grid_heat_is_more_expensive():
    result = build_smart_energy_advice(
        electricity_price=0.40,
        gas_price_per_m3=1.20,
        now=NOW,
    )
    assert result["state"] == "gas"
    assert result["cheapest_now"] == "gas"


def test_waits_for_materially_cheaper_future_electricity():
    prices = [
        PriceEntry(NOW + timedelta(minutes=15), 0.30),
        PriceEntry(NOW + timedelta(minutes=30), 0.12),
    ]
    result = build_smart_energy_advice(
        electricity_price=0.30,
        future_prices=prices,
        gas_price_per_m3=1.50,
        now=NOW,
    )
    assert result["state"] == "wait"
    assert result["minutes_until_better"] == 30
    assert result["next_better_price"] == 0.12


def test_negative_price_future_threshold_is_absolute():
    prices = [PriceEntry(NOW + timedelta(minutes=15), -0.02)]
    result = build_smart_energy_advice(
        electricity_price=-0.01,
        future_prices=prices,
        gas_price_per_m3=1.20,
        now=NOW,
    )
    assert result["next_better_price"] == -0.02


def test_missing_gas_price_remains_generic():
    result = build_smart_energy_advice(electricity_price=0.20, now=NOW, language="nl")
    assert result["state"] in {"cheap_grid", "wait"}
    assert "gasprijssensor" in result["recommendation"]
