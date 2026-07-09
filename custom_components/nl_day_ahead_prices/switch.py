"""Runtime switches for price analysis."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ALLOW_BEST_RELAXATION,
    CONF_ALLOW_PEAK_RELAXATION,
    CONF_CHART_HELPERS,
    CONF_EXTENDED_ATTRIBUTES,
    DOMAIN,
)
from .coordinator import NLDayAheadPricesCoordinator

SWITCHES = tuple(
    SwitchEntityDescription(key=key, translation_key=key)
    for key in (
        CONF_ALLOW_BEST_RELAXATION,
        CONF_ALLOW_PEAK_RELAXATION,
        CONF_EXTENDED_ATTRIBUTES,
        CONF_CHART_HELPERS,
    )
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up runtime switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AnalysisSwitch(coordinator, entry, description) for description in SWITCHES)


class AnalysisSwitch(CoordinatorEntity[NLDayAheadPricesCoordinator], SwitchEntity, RestoreEntity):
    """A switch that immediately updates coordinator analysis settings."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: NLDayAheadPricesCoordinator, entry: ConfigEntry, description: SwitchEntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": "NL Day Ahead Prices"}

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.runtime_options[self.entity_description.key])

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.update_runtime_option(self.entity_description.key, True)

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.update_runtime_option(self.entity_description.key, False)

    async def async_added_to_hass(self) -> None:
        """Restore the most recent runtime state."""
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) is not None:
            self.coordinator.runtime_options[self.entity_description.key] = state.state == "on"
