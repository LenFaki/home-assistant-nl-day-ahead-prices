"""Validated public registry transport and last-known-good storage.

The manager is shared across config entries. Only the HA adapter imports HA;
validation and transport are independently testable without a running instance.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from math import isfinite
from typing import Any
from urllib.parse import urlparse

import aiohttp

from .supplier_registry import (
    SupplierRegistry,
    activate_remote_registry,
    load_registry,
    parse_registry,
)

REMOTE_REGISTRY_URL = "https://raw.githubusercontent.com/LenFaki/home-assistant-nl-day-ahead-prices/main/registry/supplier_tariffs.json"
REMOTE_CHECK_INTERVAL = timedelta(hours=24)
REMOTE_TIMEOUT_SECONDS = 20
MAX_REGISTRY_BYTES = 1_048_576
MAX_KWH_FEE = 5
MAX_MONTHLY_FEE = 1000
NUMERIC_TARIFF_BOUNDS = {
    "purchase_fee_import": (0, MAX_KWH_FEE),
    "purchase_fee_export": (-MAX_KWH_FEE, MAX_KWH_FEE),
    "fixed_monthly_fee_electricity": (0, MAX_MONTHLY_FEE),
    "feed_in_fee": (-MAX_KWH_FEE, MAX_KWH_FEE),
    "imbalance_fee": (-MAX_KWH_FEE, MAX_KWH_FEE),
}
STORAGE_KEY = "nl_day_ahead_prices_supplier_registry"
REQUIRED_SUPPLIERS = frozenset({
    "zonneplan", "tibber", "anwb_energie", "easy_energy", "eneco", "vandebron",
    "vattenfall", "greenchoice", "energyzero", "samsam", "pure_energie",
})
TARIFF_FIELDS = frozenset({
    "valid_from", "valid_until", "purchase_fee_import", "purchase_fee_export",
    "fixed_monthly_fee_electricity", "vat_included", "export_vat_included",
    "settlement_resolution", "source_type", "source_url", "last_verified", "notes",
    "feed_in_fee", "imbalance_fee", "profile_version", "supports_hourly_prices",
    "supports_quarter_hour_prices",
})
_LOGGER = logging.getLogger(__name__)


def utc_timestamp(value: Any) -> datetime:
    """Require an ISO timestamp with an explicit UTC offset."""
    if not isinstance(value, str) or "T" not in value:
        raise ValueError("Invalid UTC timestamp")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("Timestamp must be UTC")
    return parsed


def parse_remote_registry(payload: Any) -> SupplierRegistry:
    """Validate the entire remote candidate before using the shared adapter."""
    if not isinstance(payload, dict):
        raise ValueError("Registry must be an object")
    required = {"schema_version", "revision", "country", "currency", "suppliers"}
    if not required <= payload.keys() or payload.keys() - required - {"published_at"}:
        raise ValueError("Invalid registry fields")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValueError("Unsupported schema_version")
    if type(payload["revision"]) is not int or payload["revision"] < 1:
        raise ValueError("revision must be a positive integer")
    if "published_at" in payload:
        utc_timestamp(payload["published_at"])
    suppliers = payload["suppliers"]
    if not isinstance(suppliers, dict) or not REQUIRED_SUPPLIERS <= suppliers.keys() or len(suppliers) > 100:
        raise ValueError("Missing required supplier or invalid supplier map")
    for key, supplier in suppliers.items():
        if not isinstance(key, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", key):
            raise ValueError("Invalid supplier ID")
        if not isinstance(supplier, dict) or set(supplier) != {"name", "tariffs"}:
            raise ValueError("Invalid supplier fields")
        if not isinstance(supplier["name"], str) or not 1 <= len(supplier["name"]) <= 200:
            raise ValueError("Invalid supplier name")
        records = supplier["tariffs"]
        if not isinstance(records, list) or not 1 <= len(records) <= 100:
            raise ValueError("Invalid tariff list")
        for record in records:
            if not isinstance(record, dict) or set(record) != TARIFF_FIELDS:
                raise ValueError("Invalid tariff fields")
            for field, (minimum, maximum) in NUMERIC_TARIFF_BOUNDS.items():
                value = record[field]
                if field == "imbalance_fee" and value is None:
                    continue
                if type(value) not in (int, float):
                    raise ValueError(f"{field} must be numeric, not boolean or null")
                # Integers are finite; avoid float conversion of enormous JSON integers.
                if isinstance(value, float) and not isfinite(value):
                    raise ValueError(f"{field} must be finite")
                if not minimum <= value <= maximum:
                    raise ValueError(f"{field} outside safety bounds")
            for field in ("valid_from", "valid_until", "last_verified"):
                value = record[field]
                if value is not None:
                    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                        raise ValueError("Invalid ISO date")
                    date.fromisoformat(value)
            url = record["source_url"]
            if record["source_type"] in ("official", "secondary") and url is None:
                raise ValueError("Sourced tariff requires a URL")
            if url is not None:
                if not isinstance(url, str) or len(url) > 2048 or any(c.isspace() for c in url):
                    raise ValueError("Invalid source URL")
                parsed_url = urlparse(url)
                if (parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname
                        or parsed_url.username or parsed_url.password):
                    raise ValueError("Invalid public source URL")
                _ = parsed_url.port  # Validate malformed/out-of-range ports too.
            if record["notes"] is not None and (
                not isinstance(record["notes"], str) or len(record["notes"]) > 10000
            ):
                raise ValueError("Invalid notes")
            if type(record["profile_version"]) is not int or record["profile_version"] != 2:
                raise ValueError("Invalid profile version")
    # Shared validation rejects wrong types, non-finite amounts and unsupported enums.
    parsed = parse_registry({
        "registry_version": payload["schema_version"], "country": payload["country"],
        "currency": payload["currency"], "suppliers": suppliers,
    })
    for profiles in parsed.suppliers.values():
        ordered = sorted(profiles, key=lambda p: p.valid_from or "")
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if previous.valid_until is None or current.valid_from is None or current.valid_from <= previous.valid_until:
                raise ValueError("Overlapping tariff periods")
    return SupplierRegistry(
        parsed.version,
        {key: tuple(replace(p, registry_source="remote") for p in profiles)
         for key, profiles in parsed.suppliers.items()},
        payload["revision"], payload.get("published_at"),
    )


def decode_registry(raw: bytes) -> dict:
    """Reject duplicate JSON keys as well as invalid/non-finite JSON."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("Non-finite JSON number")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)


class RemoteRegistryManager:
    """Serialize checks, persist before publication, keep failures isolated."""

    def __init__(self, session, store, bundled: SupplierRegistry, *, enabled=True, now=None):
        self.session = session
        self.store = store
        self.active = bundled
        self.enabled = enabled
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.last_check: datetime | None = None
        self.last_success: datetime | None = None
        self.last_update: datetime | None = None
        self.payload: dict | None = None
        self.listeners: set[Callable[[], None]] = set()
        self._lock = asyncio.Lock()
        self._loaded = False
        self.task = None

    async def async_load(self):
        """Load only local storage; network is never awaited during setup."""
        async with self._lock:
            if self._loaded:
                return
            try:
                cached = await self.store.async_load()
                if cached is not None:
                    if not isinstance(cached, dict):
                        raise ValueError("Invalid cache envelope")
                    candidate = None
                    if cached.get("registry") is not None:
                        candidate = parse_remote_registry(cached["registry"])
                    times = {}
                    for field in ("last_check", "last_success", "last_update"):
                        value = cached.get(field)
                        times[field] = utc_timestamp(value) if value is not None else None
                        if times[field] is not None and times[field] > self.now():
                            raise ValueError("Future cache timestamp")
                    self.last_check = times["last_check"]
                    self.last_success = times["last_success"]
                    self.last_update = times["last_update"]
                    if candidate is not None and candidate.revision > self.active.revision:
                        self.payload = cached["registry"]
                        if self.enabled:
                            self.active = candidate
                            activate_remote_registry(candidate)
            except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
                _LOGGER.warning("Supplier registry cache invalid/unavailable; using bundled data")
            self._loaded = True

    def _envelope(self, payload, success, updated):
        return {
            "registry": payload,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "last_success": success.isoformat() if success else None,
            "last_update": updated.isoformat() if updated else None,
        }

    async def _download(self):
        async with asyncio.timeout(REMOTE_TIMEOUT_SECONDS):
            async with self.session.get(REMOTE_REGISTRY_URL, allow_redirects=False) as response:
                if response.status != 200:
                    raise ValueError(f"HTTP {response.status}")
                if response.content_length is not None and response.content_length > MAX_REGISTRY_BYTES:
                    raise ValueError("Registry response too large")
                raw = bytearray()
                async for chunk in response.content.iter_chunked(16384):
                    raw.extend(chunk)
                    if len(raw) > MAX_REGISTRY_BYTES:
                        raise ValueError("Registry response too large")
                return decode_registry(bytes(raw))

    async def async_check(self):
        async with self._lock:
            now = self.now()
            if not self.enabled or (self.last_check and now - self.last_check < REMOTE_CHECK_INTERVAL):
                return False
            self.last_check = now
            try:
                # Persist attempt time before HTTP, including failed checks across restarts.
                await self.store.async_save(self._envelope(self.payload, self.last_success, self.last_update))
                payload = await self._download()
                candidate = parse_remote_registry(payload)
                if candidate.revision <= self.active.revision:
                    await self.store.async_save(self._envelope(self.payload, now, self.last_update))
                    self.last_success = now
                    return False
                await self.store.async_save(self._envelope(payload, now, now))
            except (aiohttp.ClientError, TimeoutError, OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as err:
                # Do not log payloads or response bodies, including remotely supplied strings.
                _LOGGER.warning("Supplier registry check failed (%s); retaining local data", type(err).__name__)
                return False
            self.payload = payload
            self.last_success = self.last_update = now
            self.active = candidate
            activate_remote_registry(candidate)
            for listener in tuple(self.listeners):
                try:
                    listener()
                except Exception:  # noqa: BLE001 - isolate entity callbacks from the shared update loop
                    _LOGGER.exception("Supplier registry listener failed")
            return True

    async def async_run(self):
        """Independent daily loop; managed and cancelled by the HA adapter."""
        while True:
            await self.async_check()
            remaining = REMOTE_CHECK_INTERVAL
            if self.last_check:
                remaining -= self.now() - self.last_check
            await asyncio.sleep(max(1, remaining.total_seconds()))


class ConfirmedStore:
    """Read back HA Store writes because Store logs some write errors itself."""

    def __init__(self, store, storage_errors):
        self.store = store
        self.storage_errors = storage_errors

    async def async_load(self):
        try:
            return await self.store.async_load()
        except self.storage_errors as err:
            raise OSError("Registry storage unavailable") from err

    async def async_save(self, data):
        try:
            await self.store.async_save(data)
            if await self.store.async_load() != data:
                raise OSError("Registry storage write not confirmed")
        except self.storage_errors as err:
            raise OSError("Registry storage unavailable") from err


async def async_get_manager(hass):
    """Share a manager without adding non-coordinator items to DOMAIN data."""
    from homeassistant.exceptions import HomeAssistantError
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from homeassistant.helpers.storage import Store

    if STORAGE_KEY not in hass.data:
        hass.data[STORAGE_KEY] = RemoteRegistryManager(
            async_get_clientsession(hass),
            ConfirmedStore(Store(hass, 1, STORAGE_KEY, atomic_writes=True), (HomeAssistantError, NotImplementedError)),
            load_registry(),
        )
    manager = hass.data[STORAGE_KEY]
    await manager.async_load()
    return manager


def async_subscribe(hass, manager, listener):
    """Subscribe after setup; the background task does not gate HA startup."""
    manager.listeners.add(listener)
    if manager.task is None:
        manager.task = hass.async_create_background_task(manager.async_run(), "EnerPrice supplier registry")

    def unsubscribe():
        manager.listeners.discard(listener)
        if not manager.listeners and manager.task is not None:
            manager.task.cancel()
            manager.task = None

    return unsubscribe
