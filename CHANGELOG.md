# Changelog

All notable changes to **NL Day Ahead Prices** are documented here.

## v1.4.0 - 2026-07-09

### Added

- Added all-in forecasts for the next 1, 2, 3, 4, 6, 8, 12, and 24 hours.
- Added trend, trajectory, three-level rating, five-level rating, and
  volatility analysis.
- Added configurable best and peak price periods, timing sensors, and binary
  sensors.
- Added live `number` and `switch` controls that apply without a restart.
- Added `export_chart_data` and `generate_apexcharts_config` response services.
- Added exact hour and quarter-hour boundary state updates without extra API
  polling.
- Added Home Assistant diagnostics and richer price attributes.
- Added analysis tests for hourly, quarter-hour, cache, and 23/25-hour DST days.

### Changed

- Persistent cache data now expires at the local date boundary and is rejected
  when today's prices are missing.
- Advanced analysis entities are disabled by default to keep the entity
  registry tidy.

## v1.3.0 - 2026-07-03

### Added

- Added `price_resolution` option: `auto`, `hourly`, or `quarter_hour`.
- Added automatic supplier-based price resolution.
- Added date-based Zonneplan support: hourly before 2026-08-01 and
  quarter-hour from 2026-08-01.
- Added raw source price attributes: `raw_prices`, `raw_prices_today`,
  `raw_prices_tomorrow`, and `raw_price_resolution`.
- Added converted price metadata attributes: `price_resolution`,
  `requested_price_resolution`, `effective_price_resolution`, and
  `resolution_converted`.
- Added `Effective Price Resolution` sensor.
- Added resolution-aware cheapest consecutive block attributes.

### Changed

- Nord Pool quarter-hour source prices are preserved and converted later based
  on the selected resolution.
- `Next Hour` price logic is now interval-aware and returns the next hour or
  next quarter-hour depending on the effective resolution.
- Updated Vandebron purchase and sell fee to `0.0257 EUR/kWh` including VAT.

### Fixed

- Fixed all-in price calculation by applying VAT to the bare market price.
  This addresses reported 1-3 ct/kWh differences compared to supplier apps.

## v1.2.2 - 2026-07-02

### Changed

- Improved the options flow for supplier profiles.
- The first options step now shows only provider, tax, VAT, and supplier
  selection.
- Built-in suppliers now show a confirmation screen with purchase fee, monthly
  fee, verification date, and source URL.
- Custom supplier fee fields are only shown when Custom supplier is selected.

## v1.2.0 - 2026-07-02

### Added

- Added supplier profiles in `supplier_profiles.json`.
- Added built-in profiles for Zonneplan, Tibber, ANWB Energie, EasyEnergy,
  Eneco, Vandebron, Vattenfall, Greenchoice, EnergyZero, SamSam, and Custom
  supplier.
- Added options flow fields for supplier selection, energy tax, VAT, and custom
  supplier fees.
- Added `Current All-in Price`, `Next Hour All-in Price`,
  `Average All-in Price Today`, `Lowest All-in Price Today`, and
  `Highest All-in Price Today`.
- Added `Supplier Purchase Fee`, `Supplier Monthly Fee`, and
  `Selected Supplier` sensors.
- Added all-in price attributes for today and tomorrow.
- Added supplier metadata attributes: selected supplier, purchase fee, monthly
  fee, energy tax, VAT, `last_verified`, and `source_url`.
- Added Dutch translations.

### Notes

- Supplier tariffs can change and may differ per contract. Always check your
  current supplier contract or tariff sheet.
- Fixed monthly supplier fees are exposed separately and are not automatically
  spread over kWh prices.

## v1.1.4 - 2026-07-02

### Added

- Added `Highest Energy Price Time`, a timestamp sensor for the most expensive
  hour today.

## v1.1.3 - 2026-07-02

### Changed

- Changed `Lowest Energy Price` compatibility sensor to expose the timestamp of
  the cheapest hour today.

## v1.1.2 - 2026-07-02

### Added

- Added `Lowest Energy Price` compatibility sensor.

## v1.1.1 - 2026-07-02

### Changed

- Changed daily summary sensors to use all-in prices where appropriate.

## v1.1.0 - 2026-07-02

### Added

- Added `Next Hour All-in Price`.

## v1.0.7 - 2026-07-02

### Added

- Added documentation for supplier tariff configuration.

## v1.0.6 - 2026-07-02

### Fixed

- Fixed options flow loading from the integration settings gear.

## v1.0.5 - 2026-07-02

### Fixed

- Aggregated Nord Pool 15-minute market time units into hourly averages.

## v1.0.0 - 2026-07-02

### Added

- Initial HACS-compatible custom integration.
- Added Nord Pool, Energy-Charts, optional ENTSO-E fallback, and last known
  valid prices cache.
- Added config flow, options flow, `DataUpdateCoordinator`, async provider
  fetching, sensors, binary sensor, tests, CI, and documentation.
