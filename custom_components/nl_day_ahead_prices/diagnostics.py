"""Diagnostics support for EnerPrice."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import CONF_CHART_HELPERS, CONF_ENTSOE_API_TOKEN, CONF_SELECTED_SUPPLIER, DOMAIN
from .sensor import _selected_supplier_profile, _v2_data
from .supplier_registry import tariff_metadata


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
        return {"loaded": False, "options": options, "cache_rollover_used": False, "cache_source_date": None, **coordinator.fetch_diagnostics}
    advisor = _v2_data("price_advisor", data, dt_util.now(), entry, hass.config.language)
    price_score = _v2_data("price_score", data, dt_util.now(), entry)
    supplier = _selected_supplier_profile(entry)
    return {
        "loaded": True,
        **coordinator.fetch_diagnostics,
        "cache_rollover_used": data.cache_rollover_used,
        "cache_source_date": data.cache_source_date,
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
        "advisor_status": advisor.get("state"),
        "price_score_input": {
            "score": price_score.get("score"),
            "min_reference_price": price_score.get("min_reference_price"),
            "max_reference_price": price_score.get("max_reference_price"),
            "average_reference_price": price_score.get("average_reference_price"),
        },
        "selected_planning_options": {
            "price_type": "all_in",
            "resolution": data.result.effective_price_resolution,
        },
        "supplier_profile_version": supplier.profile_version,
        "supplier_tariff": {"supplier_id": supplier.key, **tariff_metadata(supplier, dt_util.now())},
        "dashboard_helper_status": bool(coordinator.runtime_options[CONF_CHART_HELPERS]),
        "resolution_status": {
            "requested": data.result.requested_price_resolution,
            "effective": data.result.effective_price_resolution,
            "raw": data.result.raw_price_resolution,
            "converted": data.result.resolution_converted,
        },
    }
