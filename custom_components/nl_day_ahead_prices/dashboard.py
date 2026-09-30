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
    theme: str = "auto",
) -> str:
    """Generate a CasaRegie-inspired EnerPrice Sections dashboard."""
    theme_line = "" if theme == "auto" else f"theme: {theme}\n"
    columns = 1 if dashboard_type == "compact" else 2

    advisor = ""
    if include_price_advisor:
        advisor = """
          - type: markdown
            title: EnerPrice Advisor
            content: |-
              {% set a = states.sensor.nl_day_ahead_price_advisor %}
              {% set state = a.state %}
              {% set icon = {'excellent':'🟢','good':'🟢','neutral':'🟡','avoid':'🟠','critical':'🔴'}.get(state, '⚪') %}
              # {{ icon }} {{ a.attributes.title | default('EnerPrice') }}
              **{{ states('sensor.nl_day_ahead_prices_current_all_in_price') }} €/kWh** · score {{ states('sensor.nl_day_ahead_price_score') }}/100

              {{ a.attributes.summary | default(a.attributes.recommendation, true) }}

              {% if a.attributes.next_better_time %}
              **Volgende gunstiger prijs:** {{ as_timestamp(a.attributes.next_better_time) | timestamp_custom('%H:%M') }} · {{ a.attributes.next_better_price | round(3) }} €/kWh
              {% endif %}
          - type: tile
            entity: sensor.nl_day_ahead_price_advisor
            name: Advies
            vertical: false
          - type: tile
            entity: sensor.nl_day_ahead_price_score
            name: Prijsscore
            vertical: false
"""

    price_tiles = ""
    if include_all_in_price:
        price_tiles += """
          - type: tile
            entity: sensor.nl_day_ahead_prices_current_all_in_price
            name: All-in prijs nu
"""
    if include_market_price:
        price_tiles += """
          - type: tile
            entity: sensor.nl_day_ahead_prices_current_market_price
            name: Marktprijs nu
"""

    details = ""
    if dashboard_type != "compact":
        details = """
      - type: grid
        cards:
          - type: heading
            heading: Vooruitblik
            icon: mdi:clock-fast
          - type: tile
            entity: binary_sensor.nl_day_ahead_prices_tomorrow_prices_available
            name: Prijzen morgen
"""
        if include_best_periods:
            details += """
          - type: tile
            entity: binary_sensor.nl_day_ahead_prices_best_price_period
            name: Goedkoop prijsblok actief
          - type: tile
            entity: sensor.nl_day_ahead_prices_next_best_price_period_start
            name: Volgende goedkope periode
"""
        if include_supplier_info:
            details += """
          - type: tile
            entity: sensor.nl_day_ahead_prices_selected_supplier
            name: Leverancier
          - type: tile
            entity: sensor.nl_day_ahead_prices_current_provider
            name: Prijsbron
"""

    graph = ""
    if dashboard_type in {"full", "energy_advisor"}:
        graph = """
      - type: grid
        cards:
          - type: heading
            heading: Prijsverloop
            icon: mdi:chart-line
          - type: custom:apexcharts-card
            graph_span: 48h
            span:
              start: day
            now:
              show: true
              label: Nu
            series:
              - entity: sensor.nl_day_ahead_prices_current_all_in_price
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
  - title: Energieadvies
    path: energy-advisor
    type: sections
    max_columns: {columns}
    sections:
      - type: grid
        cards:
          - type: heading
            heading: Energieadvies
            icon: mdi:lightning-bolt-circle
{advisor}{price_tiles}{planner_note}{details}{graph}"""

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
