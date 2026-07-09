"""Coordinator for NL Day Ahead Prices."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_utc_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .cache import cache_is_valid
from .const import (
    CACHE_VERSION,
    CONF_COUNTRY,
    CONF_CURRENCY,
    CONF_ENABLE_ENTSOE,
    CONF_ENTSOE_API_TOKEN,
    CONF_PRICE_RESOLUTION,
    CONF_PRIMARY_PROVIDER,
    CONF_SELECTED_SUPPLIER,
    DEFAULT_COUNTRY,
    DEFAULT_CURRENCY,
    DEFAULT_PRICE_RESOLUTION,
    DEFAULT_PRIMARY_PROVIDER,
    DEFAULT_SELECTED_SUPPLIER,
    DOMAIN,
    PROVIDER_CACHE,
    PROVIDER_ENERGY_CHARTS,
    PROVIDER_ENTSOE,
    PROVIDER_NORD_POOL,
    RUNTIME_DEFAULTS,
    UPDATE_INTERVAL,
)
from .models import PriceData, PriceEntry, ProviderResult
from .price_resolution import (
    PRICE_RESOLUTION_AUTO,
    convert_prices_to_resolution,
    get_supplier_price_resolution,
    infer_price_resolution,
    normalize_price_resolution,
)
from .providers import (
    BasePriceProvider,
    EnergyChartsProvider,
    EntsoeProvider,
    NordPoolProvider,
    ProviderError,
    async_fetch_with_fallback,
)
from .supplier_profiles import load_supplier_profiles

_LOGGER = logging.getLogger(__name__)


class NLDayAheadPricesCoordinator(DataUpdateCoordinator[PriceData]):
    """Fetch prices and manage provider fallback."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.store: Store[dict[str, Any]] = Store(hass, CACHE_VERSION, f"{DOMAIN}_{entry.entry_id}")
        merged = {**entry.data, **entry.options}
        self.runtime_options = {key: merged.get(key, value) for key, value in RUNTIME_DEFAULTS.items()}
        self._remove_interval_listener = None

    async def async_start(self) -> None:
        """Start exact interval-boundary state updates without an API fetch."""
        resolution = self._effective_price_resolution(self._requested_price_resolution(), dt_util.now())
        minute = [0, 15, 30, 45] if resolution == "quarter_hour" else 0
        self._remove_interval_listener = async_track_utc_time_change(
            self.hass, self._async_interval_boundary, minute=minute, second=0
        )

    async def _async_interval_boundary(self, now: datetime) -> None:
        """Notify entities at a market interval boundary."""
        self.async_update_listeners()

    def update_runtime_option(self, key: str, value: Any) -> None:
        """Apply an analysis option without reloading the integration."""
        self.runtime_options[key] = value
        self.async_update_listeners()

    async def async_stop(self) -> None:
        """Stop the interval-boundary listener."""
        if self._remove_interval_listener is not None:
            self._remove_interval_listener()
            self._remove_interval_listener = None

    async def _async_update_data(self) -> PriceData:
        now = dt_util.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        providers = self._providers()
        try:
            result, fallback_used, errors = await async_fetch_with_fallback(providers, today, tomorrow)
        except ProviderError as err:
            cached = await self._async_load_cached()
            if cached is not None:
                cached.errors["cache_reason"] = str(err)
                return cached
            raise UpdateFailed(str(err)) from err

        result = self._convert_result_resolution(result, now)
        data = PriceData(
            result=result,
            fallback_used=fallback_used,
            last_successful_update=now,
            data_completeness=_data_completeness(result, today),
        )
        await self._async_store_cached(data)
        data.errors = errors
        return data

    def _providers(self) -> list[BasePriceProvider]:
        session = async_get_clientsession(self.hass)
        options = self.entry.options
        data = self.entry.data
        country = options.get(CONF_COUNTRY, data.get(CONF_COUNTRY, DEFAULT_COUNTRY))
        currency = options.get(CONF_CURRENCY, data.get(CONF_CURRENCY, DEFAULT_CURRENCY))
        primary = options.get(CONF_PRIMARY_PROVIDER, data.get(CONF_PRIMARY_PROVIDER, DEFAULT_PRIMARY_PROVIDER))

        by_key: dict[str, BasePriceProvider] = {
            PROVIDER_NORD_POOL: NordPoolProvider(session, country, currency),
            PROVIDER_ENERGY_CHARTS: EnergyChartsProvider(session, country, currency),
        }
        token = options.get(CONF_ENTSOE_API_TOKEN, data.get(CONF_ENTSOE_API_TOKEN))
        if options.get(CONF_ENABLE_ENTSOE, data.get(CONF_ENABLE_ENTSOE, False)) and token:
            by_key[PROVIDER_ENTSOE] = EntsoeProvider(session, token, country, currency)

        order = [primary, PROVIDER_NORD_POOL, PROVIDER_ENERGY_CHARTS, PROVIDER_ENTSOE]
        providers: list[BasePriceProvider] = []
        seen: set[str] = set()
        for key in order:
            if key in by_key and key not in seen:
                providers.append(by_key[key])
                seen.add(key)
        return providers

    async def _async_store_cached(self, data: PriceData) -> None:
        await self.store.async_save(
            {
                "provider": data.result.provider,
                "prices_today": [entry.as_attribute() for entry in data.result.prices_today],
                "prices_tomorrow": [entry.as_attribute() for entry in data.result.prices_tomorrow],
                "raw_prices_today": [entry.as_attribute() for entry in data.result.source_prices_today],
                "raw_prices_tomorrow": [entry.as_attribute() for entry in data.result.source_prices_tomorrow],
                "raw_price_resolution": data.result.raw_price_resolution,
                "requested_price_resolution": data.result.requested_price_resolution,
                "effective_price_resolution": data.result.effective_price_resolution,
                "resolution_converted": data.result.resolution_converted,
                "raw_today": data.result.raw_today,
                "raw_tomorrow": data.result.raw_tomorrow,
                "last_successful_update": data.last_successful_update.isoformat()
                if data.last_successful_update
                else None,
                "local_date": dt_util.as_local(data.last_successful_update).date().isoformat()
                if data.last_successful_update
                else None,
            }
        )

    async def _async_load_cached(self) -> PriceData | None:
        cached = await self.store.async_load()
        now = dt_util.now()
        if not cache_is_valid(cached, now):
            return None
        result = ProviderResult(
            provider=PROVIDER_CACHE,
            prices_today=_deserialize_prices(cached.get("prices_today", [])),
            prices_tomorrow=_deserialize_prices(cached.get("prices_tomorrow", [])),
            raw_prices_today=_deserialize_prices(cached.get("raw_prices_today", [])),
            raw_prices_tomorrow=_deserialize_prices(cached.get("raw_prices_tomorrow", [])),
            raw_price_resolution=cached.get("raw_price_resolution", "hourly"),
            requested_price_resolution=cached.get("requested_price_resolution", DEFAULT_PRICE_RESOLUTION),
            effective_price_resolution=cached.get("effective_price_resolution", "hourly"),
            resolution_converted=bool(cached.get("resolution_converted", False)),
            raw_today=cached.get("raw_today"),
            raw_tomorrow=cached.get("raw_tomorrow"),
        )
        if not result.prices_today:
            return None
        last_update = cached.get("last_successful_update")
        parsed_update = datetime.fromisoformat(last_update) if last_update else None
        return PriceData(
            result=result,
            fallback_used=True,
            last_successful_update=parsed_update,
            from_cache=True,
            cache_age_minutes=(now - parsed_update).total_seconds() / 60 if parsed_update else None,
            data_completeness=_data_completeness(result, now.date()),
        )

    def _convert_result_resolution(self, result: ProviderResult, now: datetime) -> ProviderResult:
        raw_prices_today = list(result.prices_today)
        raw_prices_tomorrow = list(result.prices_tomorrow)
        raw_price_resolution = result.raw_price_resolution or infer_price_resolution(
            [*raw_prices_today, *raw_prices_tomorrow]
        )
        requested_resolution = self._requested_price_resolution()
        effective_resolution = self._effective_price_resolution(requested_resolution, now)
        prices_today = convert_prices_to_resolution(raw_prices_today, effective_resolution, raw_price_resolution)
        prices_tomorrow = convert_prices_to_resolution(raw_prices_tomorrow, effective_resolution, raw_price_resolution)
        return ProviderResult(
            provider=result.provider,
            prices_today=prices_today,
            prices_tomorrow=prices_tomorrow,
            raw_today=result.raw_today,
            raw_tomorrow=result.raw_tomorrow,
            raw_prices_today=raw_prices_today,
            raw_prices_tomorrow=raw_prices_tomorrow,
            raw_price_resolution=raw_price_resolution,
            requested_price_resolution=requested_resolution,
            effective_price_resolution=effective_resolution,
            resolution_converted=raw_price_resolution != effective_resolution,
        )

    def _requested_price_resolution(self) -> str:
        options = self.entry.options
        data = self.entry.data
        return normalize_price_resolution(options.get(CONF_PRICE_RESOLUTION, data.get(CONF_PRICE_RESOLUTION)))

    def _effective_price_resolution(self, requested_resolution: str, now: datetime) -> str:
        if requested_resolution != PRICE_RESOLUTION_AUTO:
            return requested_resolution
        options = self.entry.options
        data = self.entry.data
        selected_supplier = options.get(CONF_SELECTED_SUPPLIER, data.get(CONF_SELECTED_SUPPLIER, DEFAULT_SELECTED_SUPPLIER))
        profiles = load_supplier_profiles()
        profile = profiles.get(selected_supplier) or profiles.get(DEFAULT_SELECTED_SUPPLIER)
        if profile is None:
            return "hourly"
        return get_supplier_price_resolution(profile, now)


def _deserialize_prices(entries: list[dict[str, Any]]) -> list[PriceEntry]:
    return [PriceEntry(datetime.fromisoformat(entry["time"]), float(entry["price"])) for entry in entries]


def _data_completeness(result: ProviderResult, today: Any) -> str:
    """Describe whether current and next-day data are present."""
    has_today = any(dt_util.as_local(item.time).date() == today for item in result.prices_today)
    if not has_today:
        return "missing_today"
    return "today_and_tomorrow" if result.prices_tomorrow else "today_only"
