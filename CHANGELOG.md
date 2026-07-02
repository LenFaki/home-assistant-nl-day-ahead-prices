# Changelog

All notable changes to **NL Day Ahead Prices** are documented here.

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
