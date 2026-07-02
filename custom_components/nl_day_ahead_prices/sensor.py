"""Sensors for NL Day Ahead Prices."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ENERGY_TAX_INCL_VAT,
    CONF_SUPPLIER_MARKUP_EXCL_VAT,
    CONF_VAT,
    DEFAULT_ENERGY_TAX_INCL_VAT,
    DEFAULT_SUPPLIER_MARKUP_EXCL_VAT,
    DEFAULT_VAT,
    DOMAIN,
    PROVIDER_NAMES,
)
from .coordinator import NLDayAheadPricesCoordinator
from .models import (
    PriceData,
    average_price,
    calculate_all_in_price,
    current_price,
    highest_price,
    lowest_price,
    next_hour_price,
)

EUR_PER_KWH = f"EUR/{UnitOfEnergy.KILO_WATT_HOUR}"
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class NLPriceSensorDescription(SensorEntityDescription):
    """Price sensor description."""

    value_fn: Callable[[PriceData, datetime, ConfigEntry], Any]


def _current_market(data: PriceData, now: datetime, entry: ConfigEntry) -> float | None:
    return current_price(data.result.prices, now)


def _next_hour(data: PriceData, now: datetime, entry: ConfigEntry) -> float | None:
    return next_hour_price(data.result.prices, now)


def _average_today(data: PriceData, now: datetime, entry: ConfigEntry) -> float | None:
    return average_price(data.result.prices_today)


def _average_tomorrow(data: PriceData, now: datetime, entry: ConfigEntry) -> float | None:
    return average_price(data.result.prices_tomorrow)


def _lowest_today(data: PriceData, now: datetime, entry: ConfigEntry) -> float | None:
    entry_data = lowest_price(data.result.prices_today)
    return entry_data.price if entry_data else None


def _highest_today(data: PriceData, now: datetime, entry: ConfigEntry) -> float | None:
    entry_data = highest_price(data.result.prices_today)
    return entry_data.price if entry_data else None


def _lowest_time_today(data: PriceData, now: datetime, entry: ConfigEntry) -> datetime | None:
    entry_data = lowest_price(data.result.prices_today)
    return entry_data.time if entry_data else None


def _highest_time_today(data: PriceData, now: datetime, entry: ConfigEntry) -> datetime | None:
    entry_data = highest_price(data.result.prices_today)
    return entry_data.time if entry_data else None


def _current_all_in(data: PriceData, now: datetime, entry: ConfigEntry) -> float | None:
    market = current_price(data.result.prices, now)
    if market is None:
        return None
    return _calculate_all_in(market, entry)


def _next_hour_all_in(data: PriceData, now: datetime, entry: ConfigEntry) -> float | None:
    market = next_hour_price(data.result.prices, now)
    if market is None:
        return None
    return _calculate_all_in(market, entry)


def _calculate_all_in(market: float, entry: ConfigEntry) -> float:
    options = entry.options
    return calculate_all_in_price(
        market,
        float(options.get(CONF_ENERGY_TAX_INCL_VAT, DEFAULT_ENERGY_TAX_INCL_VAT)),
        float(options.get(CONF_SUPPLIER_MARKUP_EXCL_VAT, DEFAULT_SUPPLIER_MARKUP_EXCL_VAT)),
        float(options.get(CONF_VAT, DEFAULT_VAT)),
    )


def _provider(data: PriceData, now: datetime, entry: ConfigEntry) -> str:
    return PROVIDER_NAMES.get(data.result.provider, data.result.provider)


def _last_successful(data: PriceData, now: datetime, entry: ConfigEntry) -> datetime | None:
    return data.last_successful_update


SENSORS: tuple[NLPriceSensorDescription, ...] = (
    NLPriceSensorDescription(
        key="current_market_price",
        translation_key="current_market_price",
        native_unit_of_measurement=EUR_PER_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=_current_market,
    ),
    NLPriceSensorDescription(
        key="next_hour_market_price",
        translation_key="next_hour_market_price",
        native_unit_of_measurement=EUR_PER_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=_next_hour,
    ),
    NLPriceSensorDescription(
        key="average_price_today",
        translation_key="average_price_today",
        native_unit_of_measurement=EUR_PER_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=_average_today,
    ),
    NLPriceSensorDescription(
        key="average_price_tomorrow",
        translation_key="average_price_tomorrow",
        native_unit_of_measurement=EUR_PER_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=_average_tomorrow,
    ),
    NLPriceSensorDescription(
        key="lowest_price_today",
        translation_key="lowest_price_today",
        native_unit_of_measurement=EUR_PER_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=_lowest_today,
    ),
    NLPriceSensorDescription(
        key="highest_price_today",
        translation_key="highest_price_today",
        native_unit_of_measurement=EUR_PER_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=_highest_today,
    ),
    NLPriceSensorDescription(
        key="time_of_lowest_price_today",
        translation_key="time_of_lowest_price_today",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_lowest_time_today,
    ),
    NLPriceSensorDescription(
        key="time_of_highest_price_today",
        translation_key="time_of_highest_price_today",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_highest_time_today,
    ),
    NLPriceSensorDescription(
        key="current_all_in_price",
        translation_key="current_all_in_price",
        native_unit_of_measurement=EUR_PER_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=_current_all_in,
    ),
    NLPriceSensorDescription(
        key="next_hour_all_in_price",
        translation_key="next_hour_all_in_price",
        native_unit_of_measurement=EUR_PER_KWH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=_next_hour_all_in,
    ),
    NLPriceSensorDescription(key="current_provider", translation_key="current_provider", value_fn=_provider),
    NLPriceSensorDescription(
        key="last_successful_update",
        translation_key="last_successful_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_last_successful,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator: NLDayAheadPricesCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [NLDayAheadPriceSensor(coordinator, entry, description) for description in SENSORS]
    _LOGGER.info("Adding %s NL Day Ahead Prices sensor entities", len(entities))
    async_add_entities(entities)


class NLDayAheadPriceSensor(CoordinatorEntity[NLDayAheadPricesCoordinator], SensorEntity):
    """NL Day Ahead Prices sensor."""

    entity_description: NLPriceSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NLDayAheadPricesCoordinator,
        entry: ConfigEntry,
        description: NLPriceSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "NL Day Ahead Prices",
            "manufacturer": "NL Day Ahead Prices",
        }

    @property
    def native_value(self) -> Any:
        """Return sensor value."""
        if self.coordinator.data is None:
            return None
        value = self.entity_description.value_fn(self.coordinator.data, dt_util.now(), self.entry)
        return round(value, 6) if isinstance(value, float) else value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return ApexCharts-friendly price attributes."""
        data = self.coordinator.data
        if data is None:
            return {}
        return {
            "prices": [entry.as_attribute() for entry in data.result.prices],
            "prices_today": [entry.as_attribute() for entry in data.result.prices_today],
            "prices_tomorrow": [entry.as_attribute() for entry in data.result.prices_tomorrow],
            "raw_today": data.result.raw_today,
            "raw_tomorrow": data.result.raw_tomorrow,
            "provider": data.result.provider,
            "provider_name": PROVIDER_NAMES.get(data.result.provider, data.result.provider),
            "fallback_used": data.fallback_used,
            "last_successful_update": data.last_successful_update.isoformat()
            if data.last_successful_update
            else None,
        }
