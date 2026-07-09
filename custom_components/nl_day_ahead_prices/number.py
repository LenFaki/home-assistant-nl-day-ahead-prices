"""Runtime number controls for price analysis."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntityDescription, NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_BEST_PERIOD_DURATION,
    CONF_BEST_PERIOD_FLEX,
    CONF_MINIMUM_GAP,
    CONF_PEAK_PERIOD_DURATION,
    CONF_PEAK_PERIOD_FLEX,
    CONF_STABLE_TREND_THRESHOLD,
    CONF_STRONG_TREND_THRESHOLD,
    DOMAIN,
)
from .coordinator import NLDayAheadPricesCoordinator


@dataclass(frozen=True, kw_only=True)
class AnalysisNumberDescription(NumberEntityDescription):
    """Description for a runtime number."""


NUMBERS = (
    AnalysisNumberDescription(key=CONF_BEST_PERIOD_DURATION, translation_key=CONF_BEST_PERIOD_DURATION, native_min_value=15, native_max_value=1440, native_step=15, native_unit_of_measurement="min"),
    AnalysisNumberDescription(key=CONF_PEAK_PERIOD_DURATION, translation_key=CONF_PEAK_PERIOD_DURATION, native_min_value=15, native_max_value=1440, native_step=15, native_unit_of_measurement="min"),
    AnalysisNumberDescription(key=CONF_BEST_PERIOD_FLEX, translation_key=CONF_BEST_PERIOD_FLEX, native_min_value=0, native_max_value=100, native_step=1, native_unit_of_measurement="%"),
    AnalysisNumberDescription(key=CONF_PEAK_PERIOD_FLEX, translation_key=CONF_PEAK_PERIOD_FLEX, native_min_value=0, native_max_value=100, native_step=1, native_unit_of_measurement="%"),
    AnalysisNumberDescription(key=CONF_MINIMUM_GAP, translation_key=CONF_MINIMUM_GAP, native_min_value=0, native_max_value=240, native_step=15, native_unit_of_measurement="min"),
    AnalysisNumberDescription(key=CONF_STABLE_TREND_THRESHOLD, translation_key=CONF_STABLE_TREND_THRESHOLD, native_min_value=0, native_max_value=25, native_step=0.5, native_unit_of_measurement="%"),
    AnalysisNumberDescription(key=CONF_STRONG_TREND_THRESHOLD, translation_key=CONF_STRONG_TREND_THRESHOLD, native_min_value=1, native_max_value=100, native_step=1, native_unit_of_measurement="%"),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up runtime number controls."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(AnalysisNumber(coordinator, entry, description) for description in NUMBERS)


class AnalysisNumber(CoordinatorEntity[NLDayAheadPricesCoordinator], RestoreNumber):
    """A number that immediately updates coordinator analysis settings."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: NLDayAheadPricesCoordinator, entry: ConfigEntry, description: AnalysisNumberDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": "NL Day Ahead Prices"}

    @property
    def native_value(self) -> float:
        return float(self.coordinator.runtime_options[self.entity_description.key])

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.update_runtime_option(self.entity_description.key, value)

    async def async_added_to_hass(self) -> None:
        """Restore the most recent runtime value."""
        await super().async_added_to_hass()
        if (restored := await self.async_get_last_number_data()) is not None:
            self.coordinator.runtime_options[self.entity_description.key] = restored.native_value
