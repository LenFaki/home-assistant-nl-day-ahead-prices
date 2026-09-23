"""EnerPrice integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .const import DOMAIN, MARKET_PROVIDER_DEFAULTS, RUNTIME_DEFAULTS, SUPPLIER_UPDATES_AUTOMATIC
from .supplier_registry import supplier_update_mode

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EnerPrice from a config entry."""
    from .coordinator import NLDayAheadPricesCoordinator
    from .supplier_registry import get_supplier_profiles

    _LOGGER.info("Setting up EnerPrice config entry %s", entry.entry_id)
    await hass.async_add_executor_job(get_supplier_profiles)
    from .remote_registry import async_get_manager, async_subscribe

    registry_manager = await async_get_manager(hass)
    coordinator = NLDayAheadPricesCoordinator(hass, entry)
    coordinator.registry_manager = registry_manager
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, _platforms())
    await coordinator.async_start()
    entry.async_on_unload(async_subscribe(
        hass, registry_manager, coordinator.registry_updated,
        enabled=supplier_update_mode({**entry.data, **entry.options}) == SUPPLIER_UPDATES_AUTOMATIC,
    ))
    from .services import async_register_services

    async_register_services(hass)
    hass.async_create_task(coordinator.async_refresh())
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    _LOGGER.info("EnerPrice setup finished for config entry %s", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading EnerPrice config entry %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, _platforms())
    if unload_ok:
        await hass.data[DOMAIN][entry.entry_id].async_stop()
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            from .services import async_unregister_services

            async_unregister_services(hass)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply local settings without fetching; reload only for provider changes."""
    from .remote_registry import async_update_subscription

    coordinator = hass.data[DOMAIN][entry.entry_id]
    previous = coordinator.configured_options
    current = {**entry.data, **entry.options}
    if all(previous.get(key, default) == current.get(key, default)
           for key, default in MARKET_PROVIDER_DEFAULTS.items()):
        coordinator.configured_options = current
        for key, default in RUNTIME_DEFAULTS.items():
            if previous.get(key, default) != current.get(key, default):
                coordinator.runtime_options[key] = current.get(key, default)
        async_update_subscription(
            hass, coordinator.registry_manager, coordinator.registry_updated,
            supplier_update_mode(current) == SUPPLIER_UPDATES_AUTOMATIC,
        )
        return
    await hass.config_entries.async_reload(entry.entry_id)


def _platforms() -> list:
    """Return Home Assistant platforms without importing HA during pure module tests."""
    from homeassistant.const import Platform

    return [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SWITCH]
