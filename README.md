# NL Day Ahead Prices

![NL Day Ahead Prices logo](brand/logo.png)

`home-assistant-nl-day-ahead-prices` is a HACS-compatible Home Assistant custom integration for Dutch day-ahead electricity prices.

It is inspired by the sensor and ApexCharts attribute shape of `hass-entso-e`, but it avoids depending on ENTSO-E by default. Prices are fetched from alternative providers with automatic fallback:

1. Nord Pool
2. Energy-Charts
3. Optional ENTSO-E fallback
4. Last known valid prices cache

The default bidding zone is `NL`, currency is `EUR`, and all sensor prices are exposed as `EUR/kWh`. Provider prices in `EUR/MWh` are converted automatically.

Release notes are available in [CHANGELOG.md](CHANGELOG.md) and on the GitHub
releases page.

## Installation

### HACS

1. Add this repository as a custom repository in HACS.
2. Select category `Integration`.
3. Install **NL Day Ahead Prices**.
4. Restart Home Assistant.
5. Add the integration from **Settings > Devices & services**.

Important: the HACS `update.nl_day_ahead_prices_update` entity only belongs to
HACS itself. It confirms that the custom repository is installed and can be
updated. The actual price sensors are only created after you add **NL Day Ahead
Prices** from **Settings > Devices & services > Add integration**.

### Manual

Copy `custom_components/nl_day_ahead_prices` into your Home Assistant `custom_components` directory and restart Home Assistant.

## Configuration

The config flow defaults to:

- Country / bidding zone: `NL`
- Currency: `EUR`
- Primary provider: Nord Pool
- ENTSO-E fallback: disabled

The integration uses Home Assistant's shared `aiohttp` websession, modern async config entries, options flow, and a `DataUpdateCoordinator`. API failures do not block startup as long as cached prices are available.

Nord Pool can publish Dutch day-ahead prices in 15-minute market time units.
This integration preserves those source intervals and exposes hourly or
quarter-hour prices depending on the selected price interval option.

## Troubleshooting

### I only see `update.nl_day_ahead_prices_update`

That entity is created by HACS, not by this integration. Complete the Home
Assistant setup flow:

1. Restart Home Assistant after installing or updating from HACS.
2. Go to **Settings > Devices & services**.
3. Select **Add integration**.
4. Search for **NL Day Ahead Prices**.
5. Finish the setup form with the default `NL` zone.

After that, the integration should create sensors such as
`sensor.nl_day_ahead_prices_current_market_price` and
`binary_sensor.nl_day_ahead_prices_tomorrow_prices_available`.

If **NL Day Ahead Prices** is not listed in **Add integration**, Home Assistant
has not loaded the custom component yet. Restart Home Assistant and check
**Settings > System > Logs** for `nl_day_ahead_prices`.

## Options

The all-in price can be configured in the integration options. Choose one of
the built-in Dutch dynamic supplier profiles, or select **Custom supplier** and
enter your own values.

- `selected_supplier`: default `Zonneplan`
- `price_resolution`: default `auto`
- `energy_tax`: default `0.1108` EUR/kWh, including VAT
- `vat`: default `0.21`

When you select a built-in supplier, the next screen shows the profile values
that will be used for the all-in calculation: purchase fee, monthly fee,
verification date, and source URL. When you select **Custom supplier**, the next
screen shows the custom tariff fields:

- `custom_supplier_name`
- `custom_monthly_fee_electricity`
- `custom_purchase_fee_electricity`
- `custom_purchase_fee_includes_vat`
- `custom_sell_fee_electricity`
- `custom_sell_fee_includes_vat`

Formula:

```text
all_in = market_price * (1 + vat) + energy_tax + supplier_purchase_fee_incl_vat
```

When a supplier profile marks the purchase fee as excluding VAT, the integration
uses `purchase_fee_electricity * (1 + vat)` first.

The market price from the day-ahead providers is a bare wholesale price. The
integration applies VAT to that market price before adding energy tax and the
supplier purchase fee.

`Current Market Price` and `Next Market Price` are bare market prices.
They do not include taxes, VAT, or supplier purchase fees.

The day summary sensors are all-in prices using your configured tax and
supplier settings:

- `Average Price Today`
- `Average Price Tomorrow`
- `Lowest Price Today`
- `Highest Price Today`

Use `Current All-in Price` and `Next All-in Price` for all-in prices for the
current and next interval.

## Hourly And Quarter-Hour Prices

Some suppliers settle electricity per hour, while others use quarter-hour
prices. The integration can expose either format:

- `auto`: choose the resolution from the selected supplier profile.
- `hourly`: always expose hourly prices.
- `quarter_hour`: always expose quarter-hour prices.

Zonneplan uses hourly prices until 2026-07-31 and quarter-hour prices from
2026-08-01. In `auto` mode this switch is handled from the supplier profile.

When converting quarter-hour prices to hourly prices, the integration uses the
average of the available quarter-hour entries in that hour. When converting
hourly prices to quarter-hour prices, each quarter receives the same price as
the source hour.

The original source prices remain available through:

- `raw_prices`
- `raw_prices_today`
- `raw_prices_tomorrow`
- `raw_price_resolution`

### Supplier Tariffs

Supplier-specific tariff profiles are stored in
`custom_components/nl_day_ahead_prices/supplier_profiles.json`, not hard-coded
inside Python. Each profile stores:

- display name
- monthly electricity fee
- electricity purchase fee
- whether the purchase fee includes VAT
- electricity sell fee
- whether the sell fee includes VAT
- `last_verified`
- `source_url`

Bundled profiles currently include Zonneplan, Tibber, ANWB Energie,
EasyEnergy, Eneco, Vandebron, Vattenfall, Greenchoice, EnergyZero, SamSam, and
Custom supplier.

Tariffs can change and may differ per contract. Always check your current
supplier contract or tariff sheet. The bundled `last_verified` and `source_url`
fields are only there to make the included profile data auditable.

Use the settings like this:

- `energy_tax`: Dutch energy tax in `EUR/kWh`, including VAT.
- `vat`: VAT fraction, for example `0.21`.
- `custom_purchase_fee_electricity`: supplier purchasing fee in `EUR/kWh`.
- `custom_purchase_fee_includes_vat`: enable this when your supplier publishes
  the fee including VAT.

If your supplier publishes a fee in `EUR/MWh`, convert it to `EUR/kWh`:

```text
EUR/kWh = EUR/MWh / 1000
```

Fixed monthly subscription fees are not included automatically in
`Current All-in Price`, because they are not a per-kWh market price component.
If you want to include them anyway, convert them manually to an estimated
`EUR/kWh` value based on your expected monthly consumption and add that to the
custom purchase fee.

## Entities

Sensors:

- Current Market Price
- Next Market Price
- Average Price Today
- Average Price Tomorrow
- Lowest Price Today
- Lowest Energy Price Time
- Highest Price Today
- Highest Energy Price Time
- Time Of Lowest Price Today
- Time Of Highest Price Today
- Current All-in Price
- Next All-in Price
- Average All-in Price Today
- Lowest All-in Price Today
- Highest All-in Price Today
- Supplier Purchase Fee
- Supplier Monthly Fee
- Selected Supplier
- Effective Price Resolution
- Current Provider
- Last Successful Update

Binary sensor:

- Tomorrow Prices Available
- API/Data Available
- Best Price Period (disabled by default)
- Peak Price Period (disabled by default)

### Energy Optimization Toolkit

Advanced analysis entities are disabled by default. Enable only the entities
you need from the integration's device page.

- All-in forecasts for the next 1, 2, 3, 4, 6, 8, 12, and 24 hours.
- Trend values from `strongly_falling` through `strongly_rising`, including
  `trend_value_percent` and the next trend change.
- Three-level (`low`, `normal`, `high`) and five-level price ratings.
- Volatility for today, tomorrow, and the next 24 hours with min, max, average,
  median, span, and percentage attributes.
- Best and peak period start, end, remaining time, progress, and next start.

The calculations work from actual timestamps and therefore support hourly,
quarter-hour, and 23/25-hour daylight-saving days without fixed interval
counts. The toolkit was independently implemented, with
[hass.tibber_prices](https://github.com/jpawlowski/hass.tibber_prices) credited
as product inspiration.

### Runtime Settings

The device page contains `number` controls for best/peak duration, flexibility,
minimum gap, and trend thresholds. Switches control period relaxation,
extended attributes, and chart helpers. Changes apply immediately without a
Home Assistant restart.

### Services

`nl_day_ahead_prices.export_chart_data` returns `{time, price}` data for market
or all-in prices. It supports today/tomorrow selection, automatic/hourly/
quarter-hour resolution, and optional best/peak period output.

`nl_day_ahead_prices.generate_apexcharts_config` returns a YAML string with
market, all-in, cheapest-period, and peak-period series. Call response services
from Developer Tools using the UI's response-data option.

## Attributes

Each price sensor exposes ApexCharts-friendly attributes:

- `prices`
- `prices_today`
- `prices_tomorrow`
- `all_in_prices_today`
- `all_in_prices_tomorrow`
- `raw_prices`
- `raw_prices_today`
- `raw_prices_tomorrow`
- `raw_price_resolution`
- `price_resolution`
- `requested_price_resolution`
- `effective_price_resolution`
- `resolution_converted`
- `raw_today`
- `raw_tomorrow`
- `provider`
- `fallback_used`
- `last_successful_update`
- `cache_used`
- `cache_age_minutes`
- `data_completeness`
- `current_interval_start`
- `current_interval_end`
- `next_interval_start`
- `market_price`
- `all_in_price`
- `rating_3_level`
- `rating_5_level`
- `trend`
- `trend_value_percent`
- `volatility`
- `day_min`, `day_max`, `day_average`, `day_median`
- `selected_supplier`
- `supplier_purchase_fee`
- `supplier_monthly_fee`
- `energy_tax`
- `vat`
- `supplier_profile_last_verified`
- `supplier_profile_source_url`

Price entries use this format:

```json
{
  "time": "2026-07-02T13:00:00+02:00",
  "price": 0.123456
}
```

## ApexCharts Example

```yaml
type: custom:apexcharts-card
graph_span: 48h
span:
  start: day
now:
  show: true
  label: Now
header:
  show: true
  title: NL day-ahead prices (EUR/kWh)
yaxis:
  - decimals: 3
series:
  - entity: sensor.nl_day_ahead_prices_average_price_today
    name: Market price
    stroke_width: 2
    float_precision: 4
    type: column
    opacity: 1
    data_generator: |
      return entity.attributes.prices.map((entry) => {
        return [new Date(entry.time), entry.price];
      });
```

For quarter-hour prices, the same data generator works:

```yaml
data_generator: |
  return entity.attributes.prices.map((entry) => {
    return [new Date(entry.time), entry.price];
  });
```

For today only:

```yaml
data_generator: |
  return entity.attributes.prices_today.map((entry) => {
    return [new Date(entry.time), entry.price];
      });
```

## Automation Examples

Run a boiler only during a selected best period:

```yaml
automation:
  - alias: Boiler during best price period
    triggers:
      - trigger: state
        entity_id: binary_sensor.nl_day_ahead_prices_best_price_period
        to: "on"
    actions:
      - action: switch.turn_on
        target:
          entity_id: switch.boiler
  - alias: Boiler off after best price period
    triggers:
      - trigger: state
        entity_id: binary_sensor.nl_day_ahead_prices_best_price_period
        to: "off"
    actions:
      - action: switch.turn_off
        target:
          entity_id: switch.boiler
```

Start a washing machine at the cheapest two-hour block by setting **Best Period
Duration** to `120` minutes and triggering on **Best Price Period**. For an
expensive-period notification:

```yaml
automation:
  - alias: Peak price warning
    triggers:
      - trigger: state
        entity_id: binary_sensor.nl_day_ahead_prices_peak_price_period
        to: "on"
    actions:
      - action: notify.notify
        data:
          message: "The peak electricity price period has started."
```

The ApexCharts example above can show both market and all-in price by adding a
second series using `all_in_prices_today` and `all_in_prices_tomorrow`.

## Migration From hass-entso-e

This integration keeps the key ApexCharts attribute format compatible with `hass-entso-e`: `entity.attributes.prices` remains an array of `{ time, price }` objects.

Main differences:

- Domain changes from `entsoe` to `nl_day_ahead_prices`.
- Entity IDs will be newly generated by Home Assistant.
- Prices are always normalized to `EUR/kWh`.
- ENTSO-E is optional and only used as a fallback when enabled with an API token.
- The old template-based cost modifier is replaced by explicit all-in price options for Dutch tax, supplier profiles, and VAT.

After installing, update automations and ApexCharts cards to point at the new entity IDs while keeping the same `attributes.prices` data generator pattern.
