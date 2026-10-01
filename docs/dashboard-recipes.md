# EnerPrice dashboard recipes

These recipes are copy-ready starting points for Home Assistant. Replace example entity IDs with the IDs from your installation. EnerPrice remains advisory: examples do not directly control a device unless you deliberately build an automation around the returned advice.

## 1. Current all-in price

Use a native Tile card:

```yaml
type: tile
entity: sensor.nl_day_ahead_prices_current_all_in_price
name: Electricity now
```

If your entity ID differs, select **Current All-in Price** from the EnerPrice device page.

## 2. Price Advisor

```yaml
type: tile
entity: sensor.nl_day_ahead_prices_price_advisor
name: Price advice
```

The Price Advisor is the quick price-only recommendation. It does not require gas, solar or P1 entities.

## 3. Smart hot-water advice

The Smart Energy Advisor is a response action. A practical setup uses:
- an EnerPrice config entry with current all-in prices;
- a gas-price entity in EUR/m³ (optional);
- a grid/P1 power entity in W (recommended);
- optionally the electrical demand of the flexible load in W.

Grid power must use **positive = import** and **negative = export**. Unknown or unavailable values are not treated as zero.

Example action:

```yaml
action: nl_day_ahead_prices.get_smart_energy_advice
data:
  gas_price_entity: sensor.your_gas_price
  grid_power_entity: sensor.your_grid_power
  flexible_load_power_w: 1500
  electric_efficiency: 1.0
  gas_efficiency: 0.90
  gas_kwh_per_m3: 9.769
  solar_surplus_threshold_w: 500
  language: en
```

With `flexible_load_power_w`, EnerPrice distinguishes full surplus from partial surplus. For a 1500 W load, 500 W export is 33.3% coverage rather than enough surplus to run fully on exported energy. The remaining grid share is included in the effective electric heat cost.

Useful response fields include `state`, `recommendation`, `cheapest_now`, `electric_heat_cost_per_kwh`, `effective_electric_heat_cost_per_kwh`, `gas_heat_cost_per_kwh`, `measured_solar_surplus_w`, `partial_surplus`, `surplus_coverage_percent`, `required_surplus_w`, `next_better_time` and `minutes_until_better`.

## 4. Generate an EnerPrice dashboard

Instead of writing a dashboard manually, run:

```yaml
action: nl_day_ahead_prices.generate_dashboard_yaml
data:
  dashboard_type: energy_advisor
  include_market_price: true
  include_all_in_price: true
  include_supplier_info: true
  include_best_periods: true
  include_price_advisor: true
```

Copy the returned YAML into a Home Assistant dashboard. `compact` and `full` are also available.

## 5. Safe automation pattern

Treat Smart Energy Advisor output as advice and add your own safety conditions before switching a real load. For hot water, preserve the appliance's own thermostat, legionella/hygiene program, maximum temperature, minimum run time and manufacturer controls. Never interpret an unavailable sensor as permission to switch on.

## Quick setup checklist

1. Install and configure EnerPrice.
2. Verify **Current All-in Price** has a plausible value.
3. Find the grid/P1 entity and verify its sign convention.
4. Add a gas-price entity if heat-source comparison is wanted.
5. Enter the flexible load's real electrical demand when known.
6. Test the Smart Energy Advisor manually in Developer Tools > Actions.
7. Generate/copy a dashboard recipe.
8. Only then build device-control automations with explicit safety conditions.
