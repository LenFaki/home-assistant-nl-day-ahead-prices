# NL Day Ahead Prices

![NL Day Ahead Prices logo](brand/logo.png)

`home-assistant-nl-day-ahead-prices` is a HACS-compatible Home Assistant custom integration for Dutch day-ahead electricity prices.

It is inspired by the sensor and ApexCharts attribute shape of `hass-entso-e`, but it avoids depending on ENTSO-E by default. Prices are fetched from alternative providers with automatic fallback:

1. Nord Pool
2. Energy-Charts
3. Optional ENTSO-E fallback
4. Last known valid prices cache

The default bidding zone is `NL`, currency is `EUR`, and all sensor prices are exposed as `EUR/kWh`. Provider prices in `EUR/MWh` are converted automatically.

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
This integration aggregates those values into duration-weighted hourly prices
before exposing the sensors, so `Next Hour Market Price` represents the average
price for the next full clock hour.

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

The all-in price can be configured in the integration options:

- `energy_tax_incl_vat`: default `0.1108`
- `supplier_markup_excl_vat`: default `0.01653`
- `vat`: default `0.21`

Formula:

```text
all_in = market_price + energy_tax_incl_vat + supplier_markup_excl_vat * (1 + vat)
```

`Current Market Price` and `Next Hour Market Price` are bare market prices.
They do not include taxes, VAT, or supplier markup.

The day summary sensors are all-in prices using your configured tax and
supplier settings:

- `Average Price Today`
- `Average Price Tomorrow`
- `Lowest Price Today`
- `Highest Price Today`

Use `Current All-in Price` and `Next Hour All-in Price` for all-in prices for
the current and next hour.

### Supplier Tariffs

Supplier-specific prices from providers such as Zonneplan, Tibber, ANWB, or
other dynamic contracts should be entered through the integration options. The
integration intentionally does not hard-code supplier tariffs, because those
values can change and may differ per contract.

Use the settings like this:

- `energy_tax_incl_vat`: Dutch energy tax in `EUR/kWh`, including VAT.
- `supplier_markup_excl_vat`: supplier purchasing fee or markup in `EUR/kWh`,
  excluding VAT.
- `vat`: VAT fraction, for example `0.21`.

If your supplier publishes a markup including VAT, convert it first:

```text
supplier_markup_excl_vat = supplier_markup_incl_vat / (1 + vat)
```

Example with a supplier markup of `0.0200 EUR/kWh` including VAT:

```text
0.0200 / 1.21 = 0.01653
```

If your supplier publishes a markup in `EUR/MWh`, convert it to `EUR/kWh`:

```text
EUR/kWh = EUR/MWh / 1000
```

Fixed monthly subscription fees are not included automatically in
`Current All-in Price`, because they are not a per-kWh market price component.
If you want to include them anyway, convert them manually to an estimated
`EUR/kWh` value based on your expected monthly consumption and add that to the
supplier markup.

For Zonneplan, Tibber, ANWB, or another supplier, check your current contract or
tariff sheet and enter the supplier's per-kWh markup using the rules above.

## Entities

Sensors:

- Current Market Price
- Next Hour Market Price
- Average Price Today
- Average Price Tomorrow
- Lowest Price Today
- Lowest Energy Price
- Highest Price Today
- Time Of Lowest Price Today
- Time Of Highest Price Today
- Current All-in Price
- Next Hour All-in Price
- Current Provider
- Last Successful Update

Binary sensor:

- Tomorrow Prices Available

## Attributes

Each price sensor exposes ApexCharts-friendly attributes:

- `prices`
- `prices_today`
- `prices_tomorrow`
- `raw_today`
- `raw_tomorrow`
- `provider`
- `fallback_used`
- `last_successful_update`

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

## Migration From hass-entso-e

This integration keeps the key ApexCharts attribute format compatible with `hass-entso-e`: `entity.attributes.prices` remains an array of `{ time, price }` objects.

Main differences:

- Domain changes from `entsoe` to `nl_day_ahead_prices`.
- Entity IDs will be newly generated by Home Assistant.
- Prices are always normalized to `EUR/kWh`.
- ENTSO-E is optional and only used as a fallback when enabled with an API token.
- The old template-based cost modifier is replaced by explicit all-in price options for Dutch tax, supplier markup, and VAT.

After installing, update automations and ApexCharts cards to point at the new entity IDs while keeping the same `attributes.prices` data generator pattern.
