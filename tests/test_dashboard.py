"""Tests for the adaptive EnerPrice dashboard generator."""

from custom_components.nl_day_ahead_prices.dashboard import generate_dashboard_yaml


def test_dashboard_uses_resolved_entities_and_smart_setup() -> None:
    yaml = generate_dashboard_yaml(
        dashboard_type="energy_advisor",
        language="nl",
        entity_ids={
            "current_all_in_price": "sensor.my_all_in",
            "price_advisor": "sensor.my_advisor",
            "price_score": "sensor.my_score",
        },
        smart_setup={
            "enabled": True,
            "grid_power_entity": "sensor.p1_power",
            "solar_power_entity": "sensor.solar_power",
            "gas_price_entity": "sensor.gas_price",
            "flexible_load_name": "Nymo boiler",
            "flexible_load_power_w": 1500,
        },
    )

    assert "entity: sensor.my_all_in" in yaml
    assert "entity: sensor.my_advisor" in yaml
    assert "entity: sensor.p1_power" in yaml
    assert "entity: sensor.solar_power" in yaml
    assert "entity: sensor.gas_price" in yaml
    assert "Nymo boiler · 1500 W" in yaml
    assert "heading: Smart Energy" in yaml
    assert "title: Energieadvies" in yaml


def test_dashboard_omits_smart_section_when_setup_disabled() -> None:
    yaml = generate_dashboard_yaml(
        dashboard_type="compact",
        language="en",
        smart_setup={"enabled": False},
    )

    assert "heading: Smart Energy" not in yaml
    assert "title: Energy advice" in yaml
    assert "heading: Outlook" not in yaml
    assert "custom:apexcharts-card" not in yaml


def test_dashboard_only_renders_available_optional_smart_entities() -> None:
    yaml = generate_dashboard_yaml(
        language="en",
        smart_setup={
            "enabled": True,
            "grid_power_entity": "sensor.grid",
            "solar_power_entity": None,
            "gas_price_entity": None,
        },
    )

    assert "entity: sensor.grid" in yaml
    assert "Solar production" not in yaml
    assert "Gas price" not in yaml


def test_dashboard_can_hide_smart_energy_context() -> None:
    yaml = generate_dashboard_yaml(
        include_smart_energy=False,
        smart_setup={"enabled": True, "grid_power_entity": "sensor.grid"},
    )

    assert "entity: sensor.grid" not in yaml
    assert "heading: Smart Energy" not in yaml
