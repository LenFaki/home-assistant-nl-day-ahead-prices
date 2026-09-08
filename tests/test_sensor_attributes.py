"""Public sensor attribute regressions with lightweight HA entity doubles."""

import importlib.util
import sys
from dataclasses import make_dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from custom_components.nl_day_ahead_prices.cache import get_cached_prices_for_date
from custom_components.nl_day_ahead_prices.const import CONF_EXTENDED_ATTRIBUTES, RUNTIME_DEFAULTS
from custom_components.nl_day_ahead_prices.models import PriceData, PriceEntry, ProviderResult


@pytest.fixture
def sensor_module(monkeypatch):
    class CoordinatorEntity:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, coordinator):
            self.coordinator = coordinator

    description = make_dataclass("SensorEntityDescription", [
        (key, object, None) for key in (
            "key", "translation_key", "native_unit_of_measurement", "device_class",
            "options", "state_class", "suggested_display_precision", "entity_registry_enabled_default",
        )
    ], frozen=True, kw_only=True)
    modules = {
        "homeassistant": {},
        "homeassistant.components": {},
        "homeassistant.components.sensor": {
            "SensorDeviceClass": SimpleNamespace(ENUM="enum", TIMESTAMP="timestamp"),
            "SensorStateClass": SimpleNamespace(MEASUREMENT="measurement"),
            "SensorEntity": type("SensorEntity", (), {}), "SensorEntityDescription": description,
        },
        "homeassistant.config_entries": {"ConfigEntry": object},
        "homeassistant.const": {"UnitOfEnergy": SimpleNamespace(KILO_WATT_HOUR="kWh")},
        "homeassistant.core": {"HomeAssistant": object},
        "homeassistant.helpers": {},
        "homeassistant.helpers.entity_platform": {"AddEntitiesCallback": object},
        "homeassistant.helpers.update_coordinator": {"CoordinatorEntity": CoordinatorEntity},
        "homeassistant.util": {"dt": SimpleNamespace(now=lambda: datetime(2026, 9, 8, 10, tzinfo=timezone.utc))},
        "custom_components.nl_day_ahead_prices.coordinator": {"NLDayAheadPricesCoordinator": object},
    }
    for name, attributes in modules.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        monkeypatch.setitem(sys.modules, name, module)
    name = "custom_components.nl_day_ahead_prices._sensor_test"
    path = Path(__file__).parents[1] / "custom_components/nl_day_ahead_prices/sensor.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def make_sensor(module, prices, extended=False, cached=False):
    result = ProviderResult("cache" if cached else "nord_pool", prices, [],
                            effective_price_resolution="quarter_hour" if len(prices) > 25 else "hourly")
    data = PriceData(result, cached, prices[0].time, from_cache=cached,
                     data_completeness="cache_promoted_tomorrow" if cached else "today_only")
    coordinator = SimpleNamespace(data=data, runtime_options={**RUNTIME_DEFAULTS, CONF_EXTENDED_ATTRIBUTES: extended})
    entry = SimpleNamespace(entry_id="test", data={}, options={})
    description = module.NLPriceSensorDescription(key="average_price_today", value_fn=module._average_today)
    return module.NLDayAheadPriceSensor(coordinator, entry, description)


def day_prices(day, minutes):
    zone = ZoneInfo("Europe/Amsterdam")
    start = datetime.fromisoformat(day).replace(tzinfo=zone).astimezone(timezone.utc)
    end = (datetime.fromisoformat(day).replace(tzinfo=zone) + timedelta(days=1)).astimezone(timezone.utc)
    prices = []
    while start < end:
        prices.append(PriceEntry(start.astimezone(zone), 0.1))
        start += timedelta(minutes=minutes)
    return prices


@pytest.mark.parametrize("extended", [False, True])
def test_core_and_optional_attributes(sensor_module, extended, monkeypatch):
    sensor = make_sensor(sensor_module, day_prices("2026-09-08", 60), extended)
    if not extended:
        monkeypatch.setattr(sensor_module, "_cheapest_block_attributes", Mock(side_effect=AssertionError("unneeded analysis")))
    attrs = sensor.extra_state_attributes
    required = {
        "prices", "prices_today", "prices_tomorrow", "all_in_prices_today", "all_in_prices_tomorrow",
        "raw_prices", "raw_prices_today", "raw_prices_tomorrow", "raw_price_resolution",
        "price_resolution", "requested_price_resolution", "effective_price_resolution", "resolution_converted",
        "provider", "provider_name", "fallback_used", "cache_used", "data_completeness",
        "last_successful_update", "selected_supplier", "selected_supplier_name",
    }
    assert required <= attrs.keys()
    assert ("supplier_profile" in attrs) == extended
    assert ("trend" in attrs) == extended
    assert attrs["prices_tomorrow"] == attrs["all_in_prices_tomorrow"] == []
    for key in ("prices_today", "all_in_prices_today"):
        assert isinstance(attrs[key], list)
        for item in attrs[key]:
            assert set(item) == {"time", "price"}
            assert isinstance(item["price"], (int, float))
            assert datetime.fromisoformat(item["time"]).tzinfo is not None
    assert attrs["all_in_prices_today"][0]["price"] > attrs["prices_today"][0]["price"]
    assert sensor.suggested_object_id == "nl_day_ahead_prices_average_price_today"


@pytest.mark.parametrize("day,hours", [("2026-09-08", 24), ("2026-03-29", 23), ("2026-10-25", 25)])
@pytest.mark.parametrize("minutes", [15, 60])
def test_chart_intervals_and_dst(sensor_module, day, hours, minutes):
    attrs = make_sensor(sensor_module, day_prices(day, minutes)).extra_state_attributes
    for key in ("prices_today", "all_in_prices_today"):
        values = attrs[key]
        assert len(values) == hours * 60 // minutes
        timestamps = [datetime.fromisoformat(item["time"]).timestamp() for item in values]
        assert all(b - a == minutes * 60 for a, b in zip(timestamps, timestamps[1:], strict=False))


def test_promoted_cache_chart_attributes(sensor_module):
    prices = day_prices("2026-09-08", 60)
    cached = {"local_date": "2026-09-07", "prices_tomorrow": [item.as_attribute() for item in prices]}
    restored = get_cached_prices_for_date(cached, prices[0].time.date())
    entries = [PriceEntry(datetime.fromisoformat(item["time"]), item["price"]) for item in restored["prices"]]
    attrs = make_sensor(sensor_module, entries, cached=True).extra_state_attributes
    assert restored["status"] == attrs["data_completeness"] == "cache_promoted_tomorrow"
    assert attrs["cache_used"]
    assert len(attrs["prices_today"]) == len(attrs["all_in_prices_today"]) == 24
