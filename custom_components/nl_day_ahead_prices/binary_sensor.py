"""Binary sensors for price availability and selected periods."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .analysis.periods import active_and_next
from .const import DOMAIN
from .coordinator import NLDayAheadPricesCoordinator
from .models import PriceData
from .sensor import _periods


@dataclass(frozen=True, kw_only=True)
class PriceBinaryDescription(BinarySensorEntityDescription):
    """Binary sensor description."""

    value_fn: Callable[[PriceData, NLDayAheadPricesCoordinator, ConfigEntry], bool]
    period_type: str | None = None


DESCRIPTIONS = (
    PriceBinaryDescription(
        key="tomorrow_prices_available",
        translation_key="tomorrow_prices_available",
        value_fn=lambda data, coordinator, entry: bool(data.result.prices_tomorrow),
    ),
    PriceBinaryDescription(
        key="api_data_available",
        translation_key="api_data_available",
        value_fn=lambda data, coordinator, entry: bool(data.result.prices_today),
    ),
    PriceBinaryDescription(
        key="best_price_period",
        translation_key="best_price_period",
        entity_registry_enabled_default=False,
        period_type="best",
        value_fn=lambda data, coordinator, entry: bool(
            active_and_next(_periods(data, entry, coordinator.runtime_options, peak=False), dt_util.now())[0]
        ),
    ),
    PriceBinaryDescription(
        key="peak_price_period",
        translation_key="peak_price_period",
        entity_registry_enabled_default=False,
        period_type="peak",
        value_fn=lambda data, coordinator, entry: bool(
            active_and_next(_periods(data, entry, coordinator.runtime_options, peak=True), dt_util.now())[0]
        ),
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(PriceBinarySensor(coordinator, entry, description) for description in DESCRIPTIONS)


class PriceBinarySensor(CoordinatorEntity[NLDayAheadPricesCoordinator], BinarySensorEntity):
    """A coordinator-backed price binary sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NLDayAheadPricesCoordinator, entry: ConfigEntry, description: PriceBinaryDescription) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": "NL Day Ahead Prices"}

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data, self.coordinator, self.entry)

    @property
    def extra_state_attributes(self) -> dict:
        if self.coordinator.data is None or self.entity_description.period_type is None:
            return {}
        peak = self.entity_description.period_type == "peak"
        periods = _periods(self.coordinator.data, self.entry, self.coordinator.runtime_options, peak=peak)
        active, upcoming = active_and_next(periods, dt_util.now())
        return {
            "active_period": active.as_dict() if active else None,
            "next_period": upcoming.as_dict() if upcoming else None,
            "periods": [period.as_dict() for period in periods],
        }
