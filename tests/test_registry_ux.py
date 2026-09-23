"""Per-entry registry views, shared transport and Home Assistant diagnostics."""

import asyncio
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from test_coordinator_morning import runtime as runtime
from test_remote_registry import NOW, ROOT, Response, Store, payload, setup
from test_sensor_attributes import sensor_module as sensor_module

from custom_components.nl_day_ahead_prices import _async_update_listener
from custom_components.nl_day_ahead_prices import remote_registry as remote
from custom_components.nl_day_ahead_prices import supplier_registry as registry
from custom_components.nl_day_ahead_prices.calculations import build_all_in_price_attributes_for_supplier
from custom_components.nl_day_ahead_prices.const import CONF_SUPPLIER_TARIFF_UPDATES, DOMAIN
from custom_components.nl_day_ahead_prices.models import PriceEntry
from custom_components.nl_day_ahead_prices.registry_status import registry_status, tariff_status


@pytest.fixture(autouse=True)
def reset_registry():
    registry.activate_remote_registry(None)
    yield
    registry.activate_remote_registry(None)


def fake_hass():
    def create_task(coro, name):
        coro.close()
        return Mock()
    return SimpleNamespace(data={}, async_create_background_task=Mock(side_effect=create_task),
                           config_entries=SimpleNamespace(async_reload=AsyncMock()))


async def cached_manager():
    candidate = payload(4)
    candidate["suppliers"]["anwb_energie"]["tariffs"][0]["purchase_fee_import"] = 0.04
    manager, session, store = setup()
    manager.enabled = False
    store.data = {"registry": candidate, "last_check": NOW.isoformat()}
    await manager.async_load()
    return manager, session


def test_default_automatic_without_migration():
    assert registry.supplier_update_mode({}) == "automatic"
    assert registry.supplier_update_mode({CONF_SUPPLIER_TARIFF_UPDATES: "automatic"}) == "automatic"
    assert registry.supplier_update_mode({CONF_SUPPLIER_TARIFF_UPDATES: "bundled"}) == "bundled"


@pytest.mark.parametrize("minutes", [15, 60])
async def test_two_entries_have_isolated_calculations_and_shared_updater(minutes):
    manager, session = await cached_manager()
    hass = fake_hass()
    a, b = Mock(), Mock()
    remove_b = remote.async_subscribe(hass, manager, b, enabled=False)
    assert manager.active.revision == 1
    assert not await manager.async_check()
    session.get.assert_not_called()
    remove_a = remote.async_subscribe(hass, manager, a, enabled=True)
    assert manager.active.revision == 4
    assert manager.source == "cached_remote"
    hass.async_create_background_task.assert_called_once()
    auto = registry.get_supplier_tariff("anwb_energie", NOW, mode="automatic")
    bundled = registry.get_supplier_tariff("anwb_energie", NOW, mode="bundled")
    assert auto.purchase_fee_import == 0.04
    assert bundled.purchase_fee_import == 0.018
    prices = [PriceEntry(NOW + timedelta(minutes=i * minutes), 0.1) for i in range(100)]
    a_values = build_all_in_price_attributes_for_supplier(prices, 0.1, auto, 0.21)
    b_values = build_all_in_price_attributes_for_supplier(prices, 0.1, bundled, 0.21)
    assert all(item["price"] == 0.261 for item in a_values)
    assert all(item["price"] == 0.239 for item in b_values)
    assert registry_status(manager, "automatic")["active_source"] == "cached_remote"
    assert registry_status(manager, "bundled")["active_source"] == "bundled"
    task = manager.task
    remove_b()
    task.cancel.assert_not_called()
    remove_a()
    task.cancel.assert_called_once()
    assert not manager.enabled
    assert manager.source == "bundled"


async def test_two_automatic_entries_keep_task_until_last_automatic_unloads():
    manager, _ = await cached_manager()
    hass = fake_hass()
    a, b, c = Mock(), Mock(), Mock()
    remove_a = remote.async_subscribe(hass, manager, a)
    remove_b = remote.async_subscribe(hass, manager, b)
    remove_c = remote.async_subscribe(hass, manager, c, enabled=False)
    task = manager.task
    remove_a()
    task.cancel.assert_not_called()
    remove_b()
    task.cancel.assert_called_once()
    assert manager.task is None
    assert c in manager.listeners
    remove_c()
    hass.async_create_background_task.assert_called_once()


async def test_options_switch_uses_cached_data_without_reload_or_market_refetch(runtime):
    coordinator, _, _, now = runtime
    coordinator.entry.entry_id = "test"
    coordinator.entry.options = {"selected_supplier": "anwb_energie", "price_resolution": "hourly"}
    coordinator.configured_options = dict(coordinator.entry.options)
    coordinator.data = None
    manager, session = await cached_manager()
    coordinator.registry_manager = manager
    hass = fake_hass()
    hass.data[DOMAIN] = {"test": coordinator}
    remove = remote.async_subscribe(hass, manager, coordinator.registry_updated)
    assert registry.get_supplier_tariff("anwb_energie", NOW).purchase_fee_import == 0.04
    coordinator.entry.options[CONF_SUPPLIER_TARIFF_UPDATES] = "bundled"
    await _async_update_listener(hass, coordinator.entry)
    assert manager.source == "bundled"
    assert manager.task is None
    assert not await manager.async_check()
    assert registry.get_supplier_tariff("anwb_energie", NOW, mode="bundled").purchase_fee_import == 0.018
    coordinator.entry.options[CONF_SUPPLIER_TARIFF_UPDATES] = "automatic"
    await _async_update_listener(hass, coordinator.entry)
    assert manager.active.revision == 4
    assert manager.source == "cached_remote"
    assert not await manager.async_check()  # the cache carries a recent check time
    session.get.assert_not_called()
    coordinator.async_request_refresh.assert_not_awaited()
    hass.config_entries.async_reload.assert_not_awaited()
    assert coordinator.async_update_listeners.call_count >= 3
    remove()


@pytest.mark.parametrize("status,expected", [(200, "not_modified"), (404, "http_error"), (503, "http_error")])
async def test_cached_remote_health_states(status, expected):
    manager, session, _ = setup(4, 4, status=status)
    await manager.async_load()
    assert registry_status(manager, "automatic")["active_source"] == "cached_remote"
    listener = Mock()
    manager.listeners.add(listener)
    await manager.async_check()
    info = registry_status(manager, "automatic")
    assert info["last_check_result"] == expected
    assert info["active_source"] == ("remote" if status == 200 else "cached_remote")
    assert info["revision"] == 4
    listener.assert_called_once()


@pytest.mark.parametrize("kind,expected", [
    ("timeout", "network_error"), ("invalid", "validation_error"), ("storage", "storage_error"),
])
async def test_failure_categories_never_expose_arbitrary_text(kind, expected):
    manager, session, store = setup(4, 5)
    if kind == "timeout":
        session.get.side_effect = TimeoutError("PRIVATE_HTTP_BODY")
    elif kind == "invalid":
        session.get.return_value = Response(None, raw=b"PRIVATE_HTTP_BODY")
    else:
        store.fail_revision = 5
    await manager.async_load()
    await manager.async_check()
    info = registry_status(manager, "automatic")
    assert info["last_check_result"] == expected
    assert info["active_source"] == "cached_remote"
    assert "PRIVATE_HTTP_BODY" not in json.dumps(info)
    assert "registry" not in info and "suppliers" not in info


async def test_success_new_revision_status_and_safe_attributes():
    manager, _, _ = setup(4, 5)
    await manager.async_load()
    await manager.async_check()
    info = registry_status(manager, "automatic")
    assert info["active_source"] == "remote"
    assert info["last_check_result"] == "success"
    assert not info["fallback_active"]
    assert info["last_checked"] == NOW.isoformat()
    assert info["last_successful_update"] == NOW.isoformat()
    assert info["last_registry_update"] == NOW.isoformat()
    assert info["schema_version"] == 1
    assert info["revision"] == 5


async def test_tariff_status_current_amsterdam_date_and_revision():
    manager, _, _ = setup(4)
    await manager.async_load()
    instant = datetime(2026, 8, 31, 22, 15, tzinfo=timezone.utc)
    profile = registry.get_supplier_tariff("tibber", instant)
    info = tariff_status(profile, instant, manager)
    assert info["valid_from"] == "2026-09-01"
    assert info["purchase_fee_import"] == 0.018
    assert info["registry_revision"] == 4
    assert info["registry_source"] == "cached_remote"
    # A verification timestamp in the future must not claim current freshness.
    assert info["freshness"] == "unknown"
    info = tariff_status(registry.get_supplier_tariff("tibber", NOW), NOW, manager)
    assert info["freshness"] == "current"
    assert info["verification_age_days"] == 0


@pytest.mark.parametrize("mode", ["automatic", "bundled"])
async def test_custom_status_and_values_survive_modes(sensor_module, mode):
    manager, _ = await cached_manager()
    manager.set_enabled(True)
    entry = SimpleNamespace(entry_id="test", data={}, options={
        "selected_supplier": "custom", CONF_SUPPLIER_TARIFF_UPDATES: mode,
        "custom_purchase_fee_electricity": 0.079, "custom_monthly_fee_electricity": 9.5,
    })
    coordinator = SimpleNamespace(data=None, registry_manager=manager)
    sensor = sensor_module.NLRegistryDiagnosticSensor(coordinator, entry, sensor_module.REGISTRY_SENSORS[0])
    assert sensor.available
    assert sensor.native_value == "custom"
    assert sensor.extra_state_attributes["registry_source"] == "custom"
    assert sensor.extra_state_attributes["purchase_fee_import"] == 0.079
    assert sensor.extra_state_attributes["fixed_monthly_fee_electricity"] == 9.5
    assert sensor.extra_state_attributes["registry_revision"] is None


async def test_diagnostic_entities_enabled_stable_attached_and_available_without_prices(sensor_module):
    entry = SimpleNamespace(entry_id="example", data={}, options={CONF_SUPPLIER_TARIFF_UPDATES: "bundled"})
    manager, _ = await cached_manager()
    coordinator = SimpleNamespace(data=None, registry_manager=manager)
    for description in sensor_module.REGISTRY_SENSORS:
        sensor = sensor_module.NLRegistryDiagnosticSensor(coordinator, entry, description)
        assert sensor.available
        assert sensor._attr_unique_id == f"example_{description.key}"
        assert sensor._attr_device_info["identifiers"] == {(DOMAIN, "example")}
        assert description.entity_category == "diagnostic"
        assert description.entity_registry_enabled_default
        assert sensor.native_value in description.options
        assert "suppliers" not in sensor.extra_state_attributes
    for description in sensor_module.SENSORS:
        sensor = sensor_module.NLDayAheadPriceSensor(coordinator, entry, description)
        assert sensor._attr_unique_id == f"example_{description.key}"


async def test_diagnostics_include_safe_registry_sections_without_prices(sensor_module, monkeypatch):
    name = "custom_components.nl_day_ahead_prices._diagnostics_test"
    # Diagnostics must reuse the real sensor profile selection with lightweight HA doubles.
    monkeypatch.setitem(sys.modules, "custom_components.nl_day_ahead_prices.sensor", sensor_module)
    spec = importlib.util.spec_from_file_location(name, ROOT / "custom_components/nl_day_ahead_prices/diagnostics.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manager, _ = await cached_manager()
    entry = SimpleNamespace(entry_id="PRIVATE_ID", data={"entsoe_api_token": "PRIVATE_TOKEN"}, options={
        "location": "PRIVATE_LOCATION", "consumption": "PRIVATE_CONSUMPTION",
        CONF_SUPPLIER_TARIFF_UPDATES: "bundled",
    })
    coordinator = SimpleNamespace(data=None, registry_manager=manager,
                                  fetch_diagnostics={"provider_errors": {"nord_pool": "PRIVATE_HTTP_BODY"}})
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: coordinator}})
    data = await module.async_get_config_entry_diagnostics(hass, entry)
    assert data["supplier_registry"]["active_source"] == "bundled"
    assert "freshness" in data["supplier_tariff"]
    assert "PRIVATE" not in json.dumps(data)
    assert "suppliers" not in json.dumps(data)


def test_translations_and_version():
    base = ROOT / "custom_components/nl_day_ahead_prices"
    for path in (base / "strings.json", base / "translations/en.json", base / "translations/nl.json"):
        content = json.loads(path.read_text())
        assert CONF_SUPPLIER_TARIFF_UPDATES in content["options"]["step"]["init"]["data"]
        assert set(content["selector"][CONF_SUPPLIER_TARIFF_UPDATES]["options"]) == {"automatic", "bundled"}
        assert set(content["entity"]["sensor"]["supplier_tariff_status"]["state"]) == {
            "current", "verification_recommended", "stale", "unknown", "custom",
        }
        assert set(content["entity"]["sensor"]["supplier_registry_status"]["state"]) == {
            "remote", "cached_remote", "bundled",
        }
    assert json.loads((base / "manifest.json").read_text())["version"] == "2.1.1"


async def test_shared_manager_factory_loads_cache_once_without_network(monkeypatch):
    store = Store({"registry": payload(4)})
    factory = Mock(return_value=store)
    session = Mock()
    for name, attrs in {
        "homeassistant.exceptions": {"HomeAssistantError": RuntimeError},
        "homeassistant.helpers.aiohttp_client": {"async_get_clientsession": Mock(return_value=session)},
        "homeassistant.helpers.storage": {"Store": factory},
    }.items():
        module = ModuleType(name)
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, module)
    hass = fake_hass()
    a, b = await asyncio.gather(remote.async_get_manager(hass), remote.async_get_manager(hass))
    assert a is b
    assert a.cached_registry.revision == 4
    assert a.active.revision == 1
    factory.assert_called_once()
    assert factory.call_args.kwargs["atomic_writes"] is True
    session.get.assert_not_called()


@pytest.mark.parametrize("revision", [3, 5])
async def test_disable_during_pending_check_never_reactivates_or_downgrades(revision):
    manager, _, store = setup(4, revision)
    await manager.async_load()
    started, resume = asyncio.Event(), asyncio.Event()
    async def pending():
        started.set()
        await resume.wait()
        return payload(revision)
    manager._download = pending
    checking = asyncio.create_task(manager.async_check())
    await started.wait()
    manager.set_enabled(False)
    resume.set()
    await checking
    assert manager.source == "bundled"
    assert manager.active.revision == 1
    assert store.data["registry"]["revision"] == max(4, revision)
    assert manager.last_check_result == "disabled"
    manager.set_enabled(True)
    assert manager.active.revision == max(4, revision)


async def test_real_price_arrays_recalculate_on_mode_change_without_market_fetch(runtime, sensor_module):
    from custom_components.nl_day_ahead_prices.models import PriceData, ProviderResult

    coordinator, _, _, now = runtime
    coordinator.entry.options = {"selected_supplier": "anwb_energie"}
    coordinator.configured_options = dict(coordinator.entry.options)
    prices = [PriceEntry(now + timedelta(minutes=i * 15), 0.1) for i in range(96)]
    coordinator.data = PriceData(ProviderResult("test", prices, [], raw_price_resolution="quarter_hour"), False, now)
    manager, session = await cached_manager()
    coordinator.registry_manager = manager
    hass = fake_hass()
    hass.data[DOMAIN] = {coordinator.entry.entry_id: coordinator}
    remove = remote.async_subscribe(hass, manager, coordinator.registry_updated)
    description = sensor_module.SENSORS[0]
    sensor = sensor_module.NLDayAheadPriceSensor(coordinator, coordinator.entry, description)
    before = sensor.extra_state_attributes
    coordinator.entry.options[CONF_SUPPLIER_TARIFF_UPDATES] = "bundled"
    await _async_update_listener(hass, coordinator.entry)
    after = sensor.extra_state_attributes
    for key in ("prices", "prices_today", "prices_tomorrow"):
        assert after[key] == before[key]
    for key in ("all_in_prices", "all_in_prices_today", "all_in_prices_tomorrow"):
        assert len(after[key]) == len(before[key])
        for old, new in zip(before[key], after[key], strict=True):
            assert set(new) == {"time", "price"}
            assert new["time"] == old["time"]
            assert old["price"] - new["price"] == pytest.approx(0.022)
    coordinator.async_request_refresh.assert_not_awaited()
    session.get.assert_not_called()
    remove()


@pytest.mark.parametrize("mode", ["automatic", "bundled"])
async def test_options_flow_selector_defaults_and_cache_preview(monkeypatch, mode):
    class BaseFlow:
        def __init_subclass__(cls, **kwargs):
            pass

    class Optional:
        def __init__(self, key, default=None):
            self.key, self.default = key, default

    modules = {
        "voluptuous": {"Schema": lambda data: data, "Optional": Optional, "In": lambda data: data,
                       "All": lambda *args: args, "Coerce": lambda value: value, "Range": lambda **kwargs: kwargs},
        "homeassistant": {"config_entries": SimpleNamespace(ConfigFlow=BaseFlow, OptionsFlow=BaseFlow)},
        "homeassistant.const": {"CONF_NAME": "name"},
        "homeassistant.data_entry_flow": {"FlowResult": dict},
        "homeassistant.helpers.selector": {"SelectSelector": lambda data: data, "SelectSelectorConfig": dict},
    }
    for name, attrs in modules.items():
        module = ModuleType(name)
        module.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, module)
    name = "custom_components.nl_day_ahead_prices._flow_test"
    spec = importlib.util.spec_from_file_location(name, ROOT / "custom_components/nl_day_ahead_prices/config_flow.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manager, session = await cached_manager()
    flow = module.NLDayAheadPricesOptionsFlow()
    async def executor(function):
        return function()
    flow.hass = SimpleNamespace(data={remote.STORAGE_KEY: manager}, async_add_executor_job=executor)
    data = {} if mode == "automatic" else {CONF_SUPPLIER_TARIFF_UPDATES: mode}
    schema = await flow._async_base_options_schema(data)
    marker, selector = next((key, val) for key, val in schema.items() if key.key == CONF_SUPPLIER_TARIFF_UPDATES)
    assert marker.default == mode
    assert selector["options"] == ["automatic", "bundled"]
    assert selector["translation_key"] == CONF_SUPPLIER_TARIFF_UPDATES
    profiles = await flow._async_supplier_profiles(data)
    assert profiles["anwb_energie"].purchase_fee_import == (0.04 if mode == "automatic" else 0.018)
    assert not manager.enabled
    session.get.assert_not_called()


async def test_pending_market_update_publishes_current_entry_mode(runtime, monkeypatch):
    from custom_components.nl_day_ahead_prices.models import ProviderResult

    coordinator, module, _, now = runtime
    coordinator.entry.options = {"selected_supplier": "anwb_energie"}
    candidate = payload(4)
    tariff = candidate["suppliers"]["anwb_energie"]["tariffs"][0]
    tariff["settlement_resolution"] = "quarter_hour"
    tariff["supports_quarter_hour_prices"] = True
    registry.activate_remote_registry(remote.parse_remote_registry(candidate))
    prices = [PriceEntry(now.replace(minute=0) + timedelta(minutes=i * 15), 0.1) for i in range(4)]
    fetch = AsyncMock(return_value=(ProviderResult("test", prices, [], raw_price_resolution="quarter_hour"), False, {}))
    monkeypatch.setattr(module, "async_fetch_with_fallback", fetch)
    monkeypatch.setattr(coordinator, "_providers", lambda: [])
    async def save(data):
        assert data.result.effective_price_resolution == "quarter_hour"
        coordinator.entry.options[CONF_SUPPLIER_TARIFF_UPDATES] = "bundled"
    monkeypatch.setattr(coordinator, "_async_store_cached", save)
    data = await coordinator._async_update_data()
    assert data.result.effective_price_resolution == "hourly"
    assert len(data.result.prices_today) == 1
    assert len(data.result.source_prices_today) == 4
    fetch.assert_awaited_once()


@pytest.mark.parametrize("minutes", [15, 60])
async def test_per_entry_views_keep_midnight_and_dst_tariff_selection(minutes):
    from zoneinfo import ZoneInfo

    candidate = payload(4)
    first = candidate["suppliers"]["anwb_energie"]["tariffs"][0]
    first["valid_until"] = "2026-10-24"
    candidate["suppliers"]["anwb_energie"]["tariffs"].append({
        **first, "valid_from": "2026-10-25", "valid_until": None, "purchase_fee_import": 0.04,
    })
    registry.activate_remote_registry(remote.parse_remote_registry(candidate))
    zone = ZoneInfo("Europe/Amsterdam")
    start = datetime(2026, 10, 24, 22, tzinfo=timezone.utc) - timedelta(minutes=minutes)
    prices = [PriceEntry((start + timedelta(minutes=i * minutes)).astimezone(zone), 0.1)
              for i in range(26 * 60 // minutes)]
    automatic = registry.get_supplier_tariff("anwb_energie", prices[0].time, mode="automatic")
    bundled = registry.get_supplier_tariff("anwb_energie", prices[0].time, mode="bundled")
    auto_values = build_all_in_price_attributes_for_supplier(prices, 0.1, automatic, 0.21)
    bundle_values = build_all_in_price_attributes_for_supplier(prices, 0.1, bundled, 0.21)
    assert auto_values[0]["price"] == 0.239
    assert all(value["price"] == 0.261 for value in auto_values[1:])
    assert all(value["price"] == 0.239 for value in bundle_values)
    for values in (auto_values, bundle_values):
        stamps = [datetime.fromisoformat(value["time"]).timestamp() for value in values]
        assert stamps == sorted(set(stamps))
