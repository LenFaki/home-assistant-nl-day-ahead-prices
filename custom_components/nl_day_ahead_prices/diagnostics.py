"""Diagnostics support for NL Day Ahead Prices."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ENTSOE_API_TOKEN, CONF_SELECTED_SUPPLIER, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return non-secret integration diagnostics."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    options = {**entry.data, **entry.options}
    options.pop(CONF_ENTSOE_API_TOKEN, None)
    if data is None:
        return {"loaded": False, "options": options}
    return {
        "loaded": True,
        "provider_status": data.errors,
        "selected_provider": data.result.provider,
        "fallback_used": data.fallback_used,
        "selected_supplier": options.get(CONF_SELECTED_SUPPLIER),
        "price_resolution": data.result.effective_price_resolution,
        "raw_price_resolution": data.result.raw_price_resolution,
        "intervals_today": len(data.result.prices_today),
        "intervals_tomorrow": len(data.result.prices_tomorrow),
        "last_update": data.last_successful_update.isoformat() if data.last_successful_update else None,
        "cache": {
            "used": data.from_cache,
            "age_minutes": data.cache_age_minutes,
            "data_completeness": data.data_completeness,
        },
        "options": options,
        "runtime_options": coordinator.runtime_options,
    }
