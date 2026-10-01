import sys
from types import ModuleType, SimpleNamespace

import pytest

from custom_components.nl_day_ahead_prices import async_setup
from custom_components.nl_day_ahead_prices.const import DOMAIN


class FakeServices:
    def __init__(self):
        self.registered = {}

    def has_service(self, domain, service):
        return (domain, service) in self.registered

    def async_register(self, domain, service, handler, **kwargs):
        self.registered[(domain, service)] = (handler, kwargs)

    def async_remove(self, domain, service):
        self.registered.pop((domain, service), None)


@pytest.mark.asyncio
async def test_async_setup_delegates_service_registration(monkeypatch):
    calls = []
    fake_services_module = ModuleType("custom_components.nl_day_ahead_prices.services")
    fake_services_module.async_register_services = lambda hass: calls.append(hass)
    monkeypatch.setitem(
        sys.modules,
        "custom_components.nl_day_ahead_prices.services",
        fake_services_module,
    )
    hass = SimpleNamespace(services=FakeServices(), data={})

    assert await async_setup(hass, {}) is True
    assert calls == [hass]


def test_v2_coordinator_selection_handles_zero_one_and_multiple_entries(monkeypatch):
    # services_v2 depends on Home Assistant runtime packages that are intentionally
    # not installed in the lightweight pure-Python CI environment. Stub only the
    # external modules needed to import the coordinator helper under test.
    vol = ModuleType("voluptuous")
    vol.Schema = lambda value: value
    vol.Required = lambda key, **kwargs: key
    vol.Optional = lambda key, **kwargs: key
    vol.All = lambda *args, **kwargs: args[0] if args else None
    vol.Range = lambda **kwargs: object()
    vol.In = lambda values: object()
    vol.Coerce = lambda value: value
    monkeypatch.setitem(sys.modules, "voluptuous", vol)

    homeassistant = ModuleType("homeassistant")
    helpers = ModuleType("homeassistant.helpers")
    util = ModuleType("homeassistant.util")
    monkeypatch.setitem(sys.modules, "homeassistant", homeassistant)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers", helpers)
    monkeypatch.setitem(sys.modules, "homeassistant.util", util)

    ha_core = ModuleType("homeassistant.core")
    ha_core.HomeAssistant = object
    ha_core.ServiceCall = object
    ha_core.SupportsResponse = SimpleNamespace(ONLY="only")
    monkeypatch.setitem(sys.modules, "homeassistant.core", ha_core)

    cv = ModuleType("homeassistant.helpers.config_validation")
    cv.datetime = object()
    cv.boolean = object()
    cv.string = object()
    cv.entity_id = object()
    cv.service = object()
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.config_validation", cv)

    er = ModuleType("homeassistant.helpers.entity_registry")
    monkeypatch.setitem(sys.modules, "homeassistant.helpers.entity_registry", er)

    dt_util = ModuleType("homeassistant.util.dt")
    monkeypatch.setitem(sys.modules, "homeassistant.util.dt", dt_util)

    from custom_components.nl_day_ahead_prices.services_v2 import _coordinator

    hass = SimpleNamespace(data={DOMAIN: {}})
    assert _coordinator(hass) is None

    first = object()
    hass.data[DOMAIN] = {"first": first}
    assert _coordinator(hass) is first
    assert _coordinator(hass, "first") is first
    assert _coordinator(hass, "missing") is None

    second = object()
    hass.data[DOMAIN]["second"] = second
    assert _coordinator(hass) is None
    assert _coordinator(hass, "first") is first
    assert _coordinator(hass, "second") is second
