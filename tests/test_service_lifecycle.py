from types import SimpleNamespace

import pytest

from custom_components.nl_day_ahead_prices import async_setup
from custom_components.nl_day_ahead_prices.const import DOMAIN
from custom_components.nl_day_ahead_prices.services_v2 import _coordinator


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
async def test_async_setup_registers_services_once():
    hass = SimpleNamespace(services=FakeServices(), data={})

    assert await async_setup(hass, {}) is True
    first = set(hass.services.registered)

    assert await async_setup(hass, {}) is True
    assert set(hass.services.registered) == first
    assert len(first) == 10
    assert (DOMAIN, "get_smart_energy_advice") in first
    assert (DOMAIN, "export_chart_data") in first


def test_v2_coordinator_selection_handles_zero_one_and_multiple_entries():
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
