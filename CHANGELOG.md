# Changelog

All notable changes to **EnerPrice** are documented here.

## 2.2.0

### Added

- Added a validated remote supplier tariff registry with persistent last-known-good caching and the bundled registry as an offline fallback.
- Added `Supplier Tariff Status` and `Supplier Registry Status` diagnostic sensors for tariff freshness, registry provenance and update state.
- Added per-config-entry `Automatic` and `Bundled only` supplier tariff update modes, including runtime switching without a Home Assistant restart or an extra market-price API request.
- Added safe Home Assistant diagnostics for supplier tariff and registry metadata.
- Added deterministic supplier-registry maintenance tooling with console, JSON and Markdown audit reports.
- Added a weekly GitHub supplier tariff audit that maintains one central issue for records requiring human verification.
- Added a semantic registry revision guard so tariff changes require a higher registry revision.

### Improved

- Shared the pure-Python registry validation rules between the Home Assistant runtime and maintainer tooling.
- Remote registry checks validate complete candidates before activation, persist before publication and keep cached or bundled data active when a remote check fails.
- Multiple EnerPrice config entries can independently use automatic or bundled tariff data while sharing one remote transport/cache manager.
- Supplier tariff freshness uses the existing 60/120-day verification policy and preserves date-aware historical tariff selection.
- Registry maintenance remains read-only: supplier websites are not scraped and tariff values are never changed automatically.

### Compatibility

- The integration domain remains `nl_day_ahead_prices`.
- Existing price entities, services, configuration and price-array schemas remain compatible.
- Custom supplier configuration retains precedence over registry supplier data.
- The bundled supplier registry remains available for offline use and as fallback.

## 2.1.1

### Fixed

- Corrected the current SamSam import purchase fee to EUR 0.021118/kWh including VAT; retained its historical tariff.
- Corrected easyEnergy settlement to quarter-hour prices and confirmed its VAT-inclusive import and monthly fees.

### Improved

- Reviewed Vattenfall and conservatively retained its legacy tariff because a complete replacement tariff, export-fee mapping and effective date could not be established.
- Reviewed official supplier sources on 2026-09-23, including ANWB's monthly fee and EnergyZero's VAT-exclusive fee calculation.
- Documented partial verification and export-model limitations; incomplete records retain conservative verification dates.
- Observation-date transitions do not claim a proven contract effective date. The registry remains bundled and offline-first.
- No changes to entity IDs, services, configuration or dashboard attribute schemas.

## 2.1.0

### Added

- Offline supplier tariff registry with schema validation, validity periods and deterministic date selection in Europe/Amsterdam.
- Tariff freshness, source, validity, settlement resolution and registry origin attributes and diagnostics.
- Compatibility adapter to existing supplier profiles and legacy fallback; custom options retain precedence.

### Changed

- Updated Tibber's published standard tariff from September 2026, easyEnergy import fee precision and EnergyZero's 2026 VAT-exclusive import fee.
- Added verified quarter-hour settlement for Tibber, EnergyZero and Greenchoice; preserved Zonneplan's existing dated migration.
- Kept unverified fees and their verification dates unchanged, with source quality and review limitations documented.
- Prepared a validation boundary for future remote registries without adding any network requests.

## 2.0.3

### Added

- Added `all_in_prices` as a combined all-in price array for all currently available intervals.
- ApexCharts dashboards can now use a single attribute for today and tomorrow all-in prices.

### Improved

- Combined price arrays preserve chronological order across the repeated DST hour.
- Made the market-price and all-in-price attribute APIs consistent:
  - `prices`
  - `prices_today`
  - `prices_tomorrow`
  - `all_in_prices`
  - `all_in_prices_today`
  - `all_in_prices_tomorrow`

## 2.0.2

### Fixed

- Restored core price attributes for ApexCharts and other dashboards.
- `prices_today`, `prices_tomorrow` and all-in price arrays are now always available when price data exists.
- Core dashboard attributes no longer depend on the extended-attributes setting.
- Added regression coverage for standard and quarter-hour chart data.

## v2.0.1

### Fixed

- Fixed morning price availability when tomorrow prices are not yet published.
- Fixed persistent cache rollover at midnight, including partial current-day data.
- Tomorrow-price failures no longer invalidate valid current-day prices.
- Improved Energy-Charts local-date handling for Europe/Amsterdam.
- Improved provider fallback diagnostics and scheduled hourly API refresh at minute 7.

### Added

- Added the Pure Energie supplier profile. Thanks to Henk van Donge for the
  contribution.

## v2.0.0 - EnerPrice branding

### Added

- New EnerPrice branding and central Price Advisor.
- Renamed the integration display name to EnerPrice.
- Added new logo and brand assets.
- Kept the integration domain `nl_day_ahead_prices` for backwards
  compatibility.
- Existing entities, services, and automations continue to work.
- Robust 0-100 Price Score, Today Score, and Tomorrow Score.
- EV charging, boiler, appliance, battery, and solar export planners.
- Energy Opportunity and optional cheap/expensive/opportunity binary sensors.
- Lovelace dashboard and automation YAML generators.
- Supplier profile schema v2 with import, export, feed-in, settlement, and
  capability metadata.
- Expanded diagnostics and cached v2 calculations.

### Compatibility

- The integration domain remains `nl_day_ahead_prices`.
- Existing v1.x entities, unique IDs, price attributes, and services remain
  available.
- New advanced entities are disabled by default where appropriate.

## v1.4.1 - 2026-07-09

### Changed

- Connected the chart helper switch to the calculated `best_periods` and
  `peak_periods` attributes.
- Made generated ApexCharts configurations tolerate disabled chart helpers.

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
