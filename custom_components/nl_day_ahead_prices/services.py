"""Response services for chart data."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv

from .analysis.chart_export import apexcharts_yaml, export_prices
from .calculations import calculate_all_in_price
from .const import DOMAIN
from .models import PriceEntry
from .sensor import _energy_tax, _selected_supplier_profile, _vat

EXPORT_SERVICE = "export_chart_data"
CONFIG_SERVICE = "generate_apexcharts_config"

EXPORT_SCHEMA = vol.Schema(
    {
        vol.Optional("include_today", default=True): cv.boolean,
        vol.Optional("include_tomorrow", default=True): cv.boolean,
        vol.Optional("price_type", default="all_in"): vol.In(["market", "all_in"]),
        vol.Optional("resolution", default="auto"): vol.In(["auto", "hourly", "quarter_hour"]),
        vol.Optional("include_best_periods", default=False): cv.boolean,
        vol.Optional("include_peak_periods", default=False): cv.boolean,
    }
)


def async_register_services(hass: HomeAssistant) -> None:
    """Register response services once."""
    if hass.services.has_service(DOMAIN, EXPORT_SERVICE):
        return

    async def async_export(call: ServiceCall) -> dict:
        coordinator = _coordinator(hass)
        if coordinator is None or coordinator.data is None:
            return {"prices": [], "best_periods": [], "peak_periods": []}
        data = coordinator.data
        prices = []
        if call.data["include_today"]:
            prices.extend(data.result.prices_today)
        if call.data["include_tomorrow"]:
            prices.extend(data.result.prices_tomorrow)
        if call.data["price_type"] == "all_in":
            entry = coordinator.entry
            prices = [
                PriceEntry(
                    item.time,
                    calculate_all_in_price(item.price, _energy_tax(entry), _selected_supplier_profile(entry), _vat(entry)),
                )
                for item in prices
            ]
        from .analysis.periods import find_price_periods
        from .const import (
            CONF_BEST_PERIOD_DURATION,
            CONF_BEST_PERIOD_FLEX,
            CONF_PEAK_PERIOD_DURATION,
            CONF_PEAK_PERIOD_FLEX,
        )

        runtime = coordinator.runtime_options
        return {
            "prices": export_prices(prices, call.data["resolution"]),
            "best_periods": [
                item.as_dict()
                for item in find_price_periods(prices, int(runtime[CONF_BEST_PERIOD_DURATION]), flex_percent=float(runtime[CONF_BEST_PERIOD_FLEX]))
            ] if call.data["include_best_periods"] else [],
            "peak_periods": [
                item.as_dict()
                for item in find_price_periods(prices, int(runtime[CONF_PEAK_PERIOD_DURATION]), peak=True, flex_percent=float(runtime[CONF_PEAK_PERIOD_FLEX]))
            ] if call.data["include_peak_periods"] else [],
        }

    async def async_config(call: ServiceCall) -> dict:
        coordinator = _coordinator(hass)
        entity_id = "sensor.nl_day_ahead_prices_current_market_price"
        if coordinator is not None:
            entity_id = f"sensor.{coordinator.entry.title.lower().replace(' ', '_')}_current_market_price"
        return {"yaml": apexcharts_yaml(entity_id)}

    hass.services.async_register(DOMAIN, EXPORT_SERVICE, async_export, schema=EXPORT_SCHEMA, supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, CONFIG_SERVICE, async_config, supports_response=SupportsResponse.ONLY)


def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove services when the final entry unloads."""
    hass.services.async_remove(DOMAIN, EXPORT_SERVICE)
    hass.services.async_remove(DOMAIN, CONFIG_SERVICE)


def _coordinator(hass: HomeAssistant):
    entries = hass.data.get(DOMAIN, {})
    return next(iter(entries.values()), None)
