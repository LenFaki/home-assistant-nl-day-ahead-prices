"""Lovelace dashboard and automation YAML generators."""

from __future__ import annotations


def generate_dashboard_yaml(
    dashboard_type: str = "full",
    *,
    include_market_price: bool = True,
    include_all_in_price: bool = True,
    include_supplier_info: bool = True,
    include_best_periods: bool = True,
    include_price_advisor: bool = True,
    include_ev_planner: bool = False,
    include_battery_strategy: bool = False,
    include_smart_energy: bool = True,
    theme: str = "auto",
    language: str = "auto",
    entity_ids: dict[str, str] | None = None,
    smart_setup: dict[str, object] | None = None,
) -> str:
    """Generate a CasaRegie-inspired EnerPrice Sections dashboard."""
    theme_line = "" if theme == "auto" else f"theme: {theme}\\n"
    columns = 1 if dashboard_type == "compact" else 2
    ids = {
        "price_advisor": "sensor.nl_day_ahead_price_advisor",
        "price_score": "sensor.nl_day_ahead_price_score",
        "current_all_in_price": "sensor.nl_day_ahead_prices_current_all_in_price",
        "current_market_price": "sensor.nl_day_ahead_prices_current_market_price",
        "tomorrow_prices_available": "binary_sensor.nl_day_ahead_prices_tomorrow_prices_available",
        "best_price_period": "binary_sensor.nl_day_ahead_prices_best_price_period",
        "next_best_price_period_start": "sensor.nl_day_ahead_prices_next_best_price_period_start",
        "selected_supplier": "sensor.nl_day_ahead_prices_selected_supplier",
        "current_provider": "sensor.nl_day_ahead_prices_current_provider",
        "smart_energy_advisor": "sensor.nl_day_ahead_smart_energy_advisor",
    }
    ids.update(entity_ids or {})
    # Do not guess IDs for optional entities when the Entity Registry was inspected.
    if entity_ids is not None:
        for optional_key in ("best_price_period", "next_best_price_period_start", "smart_energy_advisor"):
            if optional_key not in entity_ids:
                ids[optional_key] = None
    smart = smart_setup or {}
    lang = "nl" if language == "nl" else "en"
    labels = {
        "nl": {
            "view": "Energieadvies", "heading": "Energieadvies", "advisor": "EnerPrice Advisor",
            "advice": "Advies", "score": "Prijsscore", "all_in": "All-in prijs nu",
            "market": "Marktprijs nu", "outlook": "Vooruitblik", "tomorrow": "Prijzen morgen",
            "best": "Goedkoop prijsblok actief", "next_best": "Volgende goedkope periode",
            "supplier": "Leverancier", "provider": "Prijsbron", "chart": "Prijsverloop",
            "smart": "Smart Energy", "grid": "Netvermogen", "solar": "Zonneproductie",
            "gas": "Gasprijs", "load": "Flexibel apparaat", "now": "Nu",
            "next_better": "Volgende gunstiger prijs", "score_word": "score",
            "smart_advice": "Smart Energy advies", "heat_cost": "Warmtekosten",
        },
        "en": {
            "view": "Energy advice", "heading": "Energy advice", "advisor": "EnerPrice Advisor",
            "advice": "Advice", "score": "Price score", "all_in": "All-in price now",
            "market": "Market price now", "outlook": "Outlook", "tomorrow": "Tomorrow prices",
            "best": "Cheap price block active", "next_best": "Next cheap period",
            "supplier": "Supplier", "provider": "Price source", "chart": "Price trend",
            "smart": "Smart Energy", "grid": "Grid power", "solar": "Solar production",
            "gas": "Gas price", "load": "Flexible load", "now": "Now",
            "next_better": "Next better price", "score_word": "score",
            "smart_advice": "Smart Energy advice", "heat_cost": "Heat cost",
        },
    }[lang]

    advisor = ""
    if include_price_advisor:
        advisor = f"""
          - type: markdown
            title: {labels["advisor"]}
            content: |-
              {{% set a = states('{ids["price_advisor"]}') %}}
              {{% set summary = state_attr('{ids["price_advisor"]}', 'summary') %}}
              {{% set title = state_attr('{ids["price_advisor"]}', 'title') | default('EnerPrice', true) %}}
              {{% set icon = {{'excellent':'🟢','good':'🟢','neutral':'🟡','avoid':'🟠','critical':'🔴'}}.get(a, '⚪') %}}
              # {{{{ icon }}}} {{{{ title }}}}
              **{{{{ states('{ids["current_all_in_price"]}') }}}} €/kWh** · {labels["score_word"]} {{{{ states('{ids["price_score"]}') }}}}/100

              {{% set recommendation = summary or state_attr('{ids["price_advisor"]}', 'recommendation') %}}
              {{% if recommendation %}}
              {{{{ recommendation }}}}
              {{% endif %}}

              {{% set better_time = state_attr('{ids["price_advisor"]}', 'next_better_time') %}}
              {{% set better_price = state_attr('{ids["price_advisor"]}', 'next_better_price') %}}
              {{% if better_time and better_price is not none %}}
              **{labels["next_better"]}:** {{{{ as_timestamp(better_time) | timestamp_custom('%H:%M') }}}} · {{{{ better_price | round(3) }}}} €/kWh
              {{% endif %}}
          - type: tile
            entity: {ids["price_advisor"]}
            name: {labels["advice"]}
          - type: tile
            entity: {ids["price_score"]}
            name: {labels["score"]}
"""

    price_tiles = ""
    if include_all_in_price:
        price_tiles += f"""
          - type: tile
            entity: {ids["current_all_in_price"]}
            name: {labels["all_in"]}
"""
    if include_market_price:
        price_tiles += f"""
          - type: tile
            entity: {ids["current_market_price"]}
            name: {labels["market"]}
"""

    details = ""
    if dashboard_type != "compact":
        details = f"""
      - type: grid
        cards:
          - type: heading
            heading: {labels["outlook"]}
            icon: mdi:clock-fast
          - type: tile
            entity: {ids["tomorrow_prices_available"]}
            name: {labels["tomorrow"]}
"""
        if include_best_periods and ids.get("best_price_period"):
            details += f"""
          - type: tile
            entity: {ids["best_price_period"]}
            name: {labels["best"]}
"""
        if include_best_periods and ids.get("next_best_price_period_start"):
            details += f"""
          - type: tile
            entity: {ids["next_best_price_period_start"]}
            name: {labels["next_best"]}
"""
        if include_supplier_info:
            details += f"""
          - type: tile
            entity: {ids["selected_supplier"]}
            name: {labels["supplier"]}
          - type: tile
            entity: {ids["current_provider"]}
            name: {labels["provider"]}
"""

    smart_cards = ""
    if include_smart_energy and smart.get("enabled"):
        tiles = []
        for key, label in (
            ("grid_power_entity", labels["grid"]),
            ("solar_power_entity", labels["solar"]),
            ("gas_price_entity", labels["gas"]),
        ):
            if smart.get(key):
                tiles.append(
                    f"""          - type: tile
            entity: {smart[key]}
            name: {label}
"""
                )
        load_name = smart.get("flexible_load_name")
        load_power = smart.get("flexible_load_power_w")
        load_card = ""
        if load_name or load_power:
            name = load_name or labels["load"]
            power = f" · {float(load_power):g} W" if load_power is not None else ""
            load_card = f"""          - type: markdown
            content: "**{labels['load']}:** {name}{power}"
"""
        smart_advisor = ids.get("smart_energy_advisor")
        advisor_card = ""
        if smart_advisor:
            advisor_card = f"""          - type: markdown
            title: {labels["smart_advice"]}
            content: |-
              {{% set state = states('{smart_advisor}') %}}
              {{% set icon = {{'solar_surplus':'☀️','cheap_grid':'🟢','wait':'⏳','gas':'🔥','normal':'⚪'}}.get(state, '⚪') %}}
              # {{{{ icon }}}} {{{{ state_attr('{smart_advisor}', 'recommendation') | default('{labels["smart"]}', true) }}}}
              {{% set electric = state_attr('{smart_advisor}', 'effective_electric_heat_cost_per_kwh') %}}
              {{% set gas = state_attr('{smart_advisor}', 'gas_heat_cost_per_kwh') %}}
              {{% if electric is not none %}}**{labels["heat_cost"]}:** ⚡ {{{{ electric }}}} €/kWh{{% endif %}}
              {{% if gas is not none %}} · 🔥 {{{{ gas }}}} €/kWh{{% endif %}}
              {{% set better = state_attr('{smart_advisor}', 'next_better_time') %}}
              {{% if better %}}
              **{labels["next_better"]}:** {{{{ as_timestamp(better) | timestamp_custom('%H:%M') }}}}
              {{% endif %}}
          - type: tile
            entity: {smart_advisor}
            name: {labels["smart_advice"]}
"""
        if tiles or load_card or advisor_card:
            smart_cards = f"""
      - type: grid
        cards:
          - type: heading
            heading: {labels["smart"]}
            icon: mdi:home-lightning-bolt
{advisor_card}{''.join(tiles)}{load_card}"""

    graph = ""
    if dashboard_type in {"full", "energy_advisor"}:
        graph = f"""
      - type: grid
        cards:
          - type: heading
            heading: {labels["chart"]}
            icon: mdi:chart-line
          - type: custom:apexcharts-card
            graph_span: 48h
            span:
              start: day
            now:
              show: true
              label: {labels["now"]}
            series:
              - entity: {ids["current_all_in_price"]}
                name: All-in
                data_generator: |
                  return [...(entity.attributes.all_in_prices_today ?? []), ...(entity.attributes.all_in_prices_tomorrow ?? [])]
                    .map(p => [new Date(p.time).getTime(), p.price]);
"""

    planner_note = ""
    if include_ev_planner or include_battery_strategy:
        planner_note = """
          - type: markdown
            content: >-
              Gebruik Ontwikkelaarstools > Acties voor de EnerPrice EV- of
              batterijplanner. De planner wijzigt apparaten niet zelfstandig.
"""

    return f"""{theme_line}title: EnerPrice
views:
  - title: {labels["view"]}
    path: energy-advisor
    type: sections
    max_columns: {columns}
    sections:
      - type: grid
        cards:
          - type: heading
            heading: {labels["heading"]}
            icon: mdi:lightning-bolt-circle
{advisor}{price_tiles}{planner_note}{smart_cards}{details}{graph}"""

def generate_automation_yaml(
    automation_type: str,
    target_entity: str,
    *,
    notify_service: str = "notify.notify",
    duration_minutes: int = 120,
    deadline: str | None = None,
) -> str:
    """Generate an editable Home Assistant automation."""
    binary = {
        "boiler_best_period": "binary_sensor.nl_day_ahead_prices_best_price_period",
        "notify_expensive_period": "binary_sensor.nl_day_ahead_expensive_energy_now",
        "notify_cheap_period": "binary_sensor.nl_day_ahead_cheap_energy_now",
        "appliance_best_window": "binary_sensor.nl_day_ahead_prices_best_price_period",
        "battery_charge_discharge": "binary_sensor.nl_day_ahead_prices_best_price_period",
        "ev_charge_before_deadline": "binary_sensor.nl_day_ahead_prices_best_price_period",
    }[automation_type]
    is_notification = automation_type.startswith("notify_")
    action = (
        f"""      - action: {notify_service}
        data:
          message: "EnerPrice notification for {target_entity}."
"""
        if is_notification
        else f"""      - action: homeassistant.turn_on
        target:
          entity_id: {target_entity}
"""
    )
    deadline_note = f"\n# Desired deadline: {deadline}" if deadline else ""
    return f"""alias: EnerPrice {automation_type.replace("_", " ")}
description: Generated by EnerPrice; review entity IDs before enabling.
triggers:
  - trigger: state
    entity_id: {binary}
    to: "on"
conditions: []
actions:
{action}mode: single
# Suggested duration: {duration_minutes} minutes{deadline_note}
"""
