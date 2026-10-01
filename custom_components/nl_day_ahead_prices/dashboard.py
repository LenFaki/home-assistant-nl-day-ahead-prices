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
    include_price_chart: bool = True,
    include_ev_planner: bool = False,
    include_battery_strategy: bool = False,
    theme: str = "auto",
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
    }
    ids.update(entity_ids or {})
    smart = smart_setup or {}

    advisor = ""
    if include_price_advisor:
        advisor = f"""
          - type: markdown
            title: EnerPrice Advisor
            content: |-
              {{% set a = states('{ids["price_advisor"]}') %}}
              {{% set summary = state_attr('{ids["price_advisor"]}', 'summary') %}}
              {{% set title = state_attr('{ids["price_advisor"]}', 'title') | default('EnerPrice', true) %}}
              {{% set icon = {{'excellent':'🟢','good':'🟢','neutral':'🟡','avoid':'🟠','critical':'🔴'}}.get(a, '⚪') %}}
              # {{{{ icon }}}} {{{{ title }}}}
              **{{{{ states('{ids["current_all_in_price"]}') }}}} €/kWh** · score {{{{ states('{ids["price_score"]}') }}}}/100

              {{{{ summary | default(state_attr('{ids["price_advisor"]}', 'recommendation'), true) }}}}

              {{% set better_time = state_attr('{ids["price_advisor"]}', 'next_better_time') %}}
              {{% set better_price = state_attr('{ids["price_advisor"]}', 'next_better_price') %}}
              {{% if better_time and better_price is not none %}}
              **Volgende gunstiger prijs:** {{{{ as_timestamp(better_time) | timestamp_custom('%H:%M') }}}} · {{{{ better_price | round(3) }}}} €/kWh
              {{% endif %}}
          - type: tile
            entity: {ids["price_advisor"]}
            name: Advies
          - type: tile
            entity: {ids["price_score"]}
            name: Prijsscore
"""

    smart_energy = ""
    if dashboard_type == "energy_advisor" and smart.get("enabled"):
        grid_entity = smart.get("grid_power_entity")
        solar_entity = smart.get("solar_power_entity")
        gas_entity = smart.get("gas_price_entity")
        load_name = str(smart.get("flexible_load_name") or "Flexible load")
        load_power = smart.get("flexible_load_power_w")
        electric_efficiency = smart.get("electric_efficiency", 1.0)
        gas_efficiency = smart.get("gas_efficiency", 0.90)
        gas_kwh = smart.get("gas_kwh_per_m3", 9.769)

        grid_expr = (
            f"states('{grid_entity}') | float(none)"
            if grid_entity
            else "none"
        )
        solar_expr = (
            f"states('{solar_entity}') | float(none)"
            if solar_entity
            else "none"
        )
        gas_expr = (
            f"states('{gas_entity}') | float(none)"
            if gas_entity
            else "none"
        )
        load_expr = str(float(load_power)) if load_power is not None else "none"
        smart_energy = f"""
      - type: grid
        cards:
          - type: heading
            heading: Smart Energy
            icon: mdi:home-lightning-bolt
          - type: markdown
            title: {load_name}
            content: |-
              {{% set price = states('{ids["current_all_in_price"]}') | float(none) %}}
              {{% set grid = {grid_expr} %}}
              {{% set solar = {solar_expr} %}}
              {{% set gas = {gas_expr} %}}
              {{% set load = {load_expr} %}}
              {{% set electric_eff = {float(electric_efficiency)} %}}
              {{% set gas_eff = {float(gas_efficiency)} %}}
              {{% set gas_kwh = {float(gas_kwh)} %}}
              {{% set measured = [0, -grid] | max if grid is not none else none %}}
              {{% set fallback = [0, solar] | max if measured is none and solar is not none else none %}}
              {{% set available = measured if measured is not none else fallback %}}
              {{% set coverage = ([100, available / load * 100] | min) if available is not none and load else none %}}
              {{% set electric_cost = price / electric_eff if price is not none and electric_eff > 0 else none %}}
              {{% set grid_share = (([0, load - available] | max) / load) if load and available is not none else 1 %}}
              {{% set effective_cost = electric_cost * grid_share if electric_cost is not none else none %}}
              {{% set gas_cost = gas / (gas_kwh * gas_eff) if gas is not none and gas_kwh > 0 and gas_eff > 0 else none %}}
              {{% set better_time = state_attr('{ids["price_advisor"]}', 'next_better_time') %}}
              {{% set wait = state_attr('{ids["price_advisor"]}', 'minutes_until_better') %}}
              {{% if load and measured is not none and measured >= load %}}
                {{% set status = '🟢 Gebruik nu' %}}
                {{% set reason = 'De volledige ingestelde belasting kan door gemeten teruglevering worden gedekt.' %}}
              {{% elif load and measured is not none and measured > 0 %}}
                {{% set status = '🟢 Gedeeltelijk overschot' %}}
                {{% set reason = 'Een deel van de belasting kan door gemeten teruglevering worden gedekt.' %}}
              {{% elif effective_cost is not none and gas_cost is not none and effective_cost <= gas_cost %}}
                {{% set status = '🟢 Elektrisch gunstig' %}}
                {{% set reason = 'De ingekochte elektrische energie is in dit model nu voordeliger dan gas.' %}}
              {{% elif gas_cost is not none and effective_cost is not none %}}
                {{% set status = '🟠 Gas gunstiger' %}}
                {{% set reason = 'Gas heeft op dit moment lagere berekende kosten per kWh bruikbare warmte.' %}}
              {{% elif price is not none %}}
                {{% set status = '🟡 Prijsadvies beschikbaar' %}}
                {{% set reason = 'Niet alle optionele Smart Energy-bronnen zijn beschikbaar.' %}}
              {{% else %}}
                {{% set status = '⚪ Onvoldoende gegevens' %}}
                {{% set reason = 'De actuele stroomprijs is niet beschikbaar.' %}}
              {{% endif %}}
              ## {{{{ status }}}}
              **Stroom nu:** {{{{ ('€ %.3f/kWh' | format(price)) if price is not none else 'niet beschikbaar' }}}}  
              **Elektrisch effectief:** {{{{ ('€ %.3f/kWh' | format(effective_cost)) if effective_cost is not none else 'niet beschikbaar' }}}}  
              **Gas bruikbare warmte:** {{{{ ('€ %.3f/kWh' | format(gas_cost)) if gas_cost is not none else 'niet beschikbaar' }}}}  
              **Gemeten overschot:** {{{{ ('%.0f W' | format(measured)) if measured is not none else 'niet beschikbaar' }}}}  
              **{load_name}:** {{{{ ('%.0f W' | format(load)) if load else 'niet ingesteld' }}}}  
              **Dekking overschot:** {{{{ ('%.0f%%' | format(coverage)) if coverage is not none else 'niet beschikbaar' }}}}

              **Advies:** {{{{ reason }}}}
              {{% if measured is none and fallback is not none %}}
              _Zonneproductie ({{{{ '%.0f W' | format(fallback) }}}}) is alleen fallback-context; dit is geen gemeten netto-overschot._
              {{% endif %}}
              {{% if better_time %}}
              **Volgende duidelijk gunstiger interval:** {{{{ as_timestamp(better_time) | timestamp_custom('%H:%M') }}}}{{% if wait is not none %}} (over {{{{ wait }}}} min){{% endif %}}
              {{% endif %}}
              _Kostenmodel: alleen ingekochte energie; gemiste terugleververgoeding is niet meegerekend._
"""
    price_tiles = ""
    if include_all_in_price:
        price_tiles += f"""
          - type: tile
            entity: {ids["current_all_in_price"]}
            name: All-in prijs nu
"""
    if include_market_price:
        price_tiles += f"""
          - type: tile
            entity: {ids["current_market_price"]}
            name: Marktprijs nu
"""

    details = ""
    if dashboard_type != "compact":
        details = f"""
      - type: grid
        cards:
          - type: heading
            heading: Vooruitblik
            icon: mdi:clock-fast
          - type: tile
            entity: {ids["tomorrow_prices_available"]}
            name: Prijzen morgen
"""
        if include_best_periods:
            details += f"""
          - type: tile
            entity: {ids["best_price_period"]}
            name: Goedkoop prijsblok actief
          - type: tile
            entity: {ids["next_best_price_period_start"]}
            name: Volgende goedkope periode
"""
        if include_supplier_info:
            details += f"""
          - type: tile
            entity: {ids["selected_supplier"]}
            name: Leverancier
          - type: tile
            entity: {ids["current_provider"]}
            name: Prijsbron
"""

    graph = ""
    if include_price_chart and dashboard_type in {"full", "energy_advisor"}:
        graph = f"""
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
{advisor}{price_tiles}{planner_note}{smart_energy}{details}{graph}"""

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
