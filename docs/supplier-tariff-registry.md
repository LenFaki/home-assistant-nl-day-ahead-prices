# Supplier Tariff Registry v1

The bundled `supplier_tariffs.json` is an offline registry, not a live tariff
service. Schema version 1 contains `country: NL`, `currency: EUR` and a supplier
map using the existing IDs. Each supplier has a name and a list of tariff records.

## Selection and fallback

Dates use Europe/Amsterdam. `valid_from` and `valid_until` are inclusive ISO dates;
null means an unknown/unbounded boundary, never an invented contract start.
The unknown start is used for migrated legacy snapshots. Future records are not
selected early and expired records are not selected. Overlaps log a warning:
newest start wins, with the last file record breaking equal-start ties.

Custom user options take precedence. Otherwise select an active bundled record,
then use the unchanged `supplier_profiles.json` as legacy fallback when the
registry is invalid, missing or has no applicable record. Unknown suppliers keep
the existing custom-supplier fallback. A legacy fallback has no certified validity
period and reports `supplier_registry_source: legacy`. It is not a newly verified
tariff. The schema validator rejects a malformed registry as a unit.

An executor-backed setup/config flow loads the JSON once. Entity reads and
date selection use in-memory data. Selection is not cached by supplier alone:
the current local date is evaluated again, including after midnight. Each all-in
price interval uses the tariff valid on that interval's Europe/Amsterdam local
date. Tomorrow's prices therefore already reflect a tariff change effective
tomorrow, even before midnight. Calculations reuse selected profiles per date
within the call only. Custom settings apply unchanged to every interval; entity
metadata continues to describe the supplier tariff valid now.

## Amounts and compatibility

Import/export fees use EUR/kWh; fixed fees use EUR/month. `vat_included` applies
to the import fee, and `export_vat_included` can override it for export. Monthly
fees are stored including VAT and are not added to per-kWh all-in prices.
`feed_in_fee` and `imbalance_fee` retain the existing VAT-inclusive semantics.
Negative export fees remain supported. The adapter populates existing v1/v2
profile fields, so entities, services, options and the `{time, price}` schema
keep working without migration. Legacy file values are intentionally frozen.

`settlement_resolution` is hourly or quarter_hour for each period; existing
capability fields and profile version 2 remain available. Zonneplan's original
August 2026 migration is represented by two registry periods.

## Freshness

`current`: 0-60 days; `verification_recommended`: 61-120 days; `stale`: over
120 days; `unknown`: missing, malformed or future verification date.
Custom configurations report `custom`. These are advisory attributes, never
availability gates. Source quality is independent: supplier-owned information
is `official`, comparison sites such as jeroen.nl are `secondary`.

A record's last_verified is conservatively retained when only some fields
were checked. Notes explain partial verification and contract limitations.
As of 2026-09-23 Tibber's new standard record is current; the ten other built-in
commercial suppliers recommend verification (none is over 120 days old).
Historical snapshots are preserved as previously bundled data, not certified
historical contract prices.

## Source review: 2026-09-23

| Supplier | Result and official reference |
| --- | --- |
| Zonneplan | Import EUR 0.0200 incl VAT and quarter-hour pricing confirmed on [dynamic contract page](https://www.zonneplan.nl/energie/dynamisch-energiecontract). Monthly/export values retained; no new full-profile verification claim. Zonnebonus is not modeled. |
| Tibber | [Standard contract](https://tibber.com/nl/energiecontract) confirms EUR 0.0180 import/export incl VAT, EUR 6.99/month from September 1 and quarter-hour pricing. [Support](https://support.tibber.com/nl/articles/5605892-de-kosten-bij-tibber) says older contracts can retain their agreed monthly fee; use custom settings if applicable. |
| ANWB Energie | [Current tariffs](https://www.anwb.nl/energie/actuele-tarieven) confirms EUR 0.018 incl VAT and hourly prices; [contract explanation](https://www.anwb.nl/energie/hoe-werkt-anwb-energie) confirms EUR 8.50/month. Export remains unverified; the complete-record date is unchanged. |
| easyEnergy | [Official tariffs](https://www.easyenergy.com/klantenservice/onze-tarieven) confirms EUR 0.02178/kWh and EUR 7/month including VAT, plus quarter-hour electricity pricing. Current settlement corrected; export remains legacy/unverified. |
| EnergyZero | [Official 2026 fee table](https://support.energyzero.nl/hc/nl/articles/7986421808285-Hoe-is-de-inkoopvergoeding-opgebouwd-voor-consumenten) gives EUR 0.028 excluding VAT. [Current prices](https://www.energyzero.nl/actuele-prijzen) confirms quarter-hour settlement from January 1, 2026. Export and monthly fees remain legacy values including VAT. |
| Greenchoice | [Dynamic contract](https://www.greenchoice.nl/stroom-en-gas/dynamisch-energiecontract/) confirms quarter-hour settlement, not a universal numeric fee. Fees retain secondary provenance. September 23 is an observation date, not a claimed contract-change date. |
| Vandebron | A generic EUR 0.02 example does not establish a universal fee. EUR 0.0257 and existing source date retained; verify the individual tariff sheet. |
| SamSam | [Official tariffs](https://samsam.nu/groene-energie) confirms EUR 0.021118/kWh including VAT, EUR 7.99/month per connection and hourly electricity. Corrected import from the observation date; historical EUR 0.0339 remains intact. Export EUR 0.0339 is unverified legacy data, not an official current amount. |
| Eneco | [Dynamic tariffs](https://www.eneco.nl/duurzame-energie/dynamisch-energiecontract/dynamische-tarieven/) explains the mechanism without establishing exact universal current fees. EUR 0.0241/kWh and EUR 7/month retain secondary provenance and their old verification date. |
| Vattenfall | [FlexPrijs with solar panels](https://www.vattenfall.nl/energie/dynamisch-energiecontract/zonnepanelen/) reviewed on 2026-09-23 did not establish a complete replacement tariff, its actual effective date and the exact mapping to EnerPrice's export-fee semantics. The single legacy record remains secondary/unverified: EUR 0.0255/kWh import and export, EUR 7.95/month. No new validity boundary or verification date. |
| Pure Energie | [Fee explanation](https://pure-energie.nl/kennisbank/inkoop-en-verkoopvergoeding-dynamisch-contract/) explains the components, but does not establish current universal amounts. Retain contributed values, including the export sign, pending contract verification. |

For easyEnergy, Greenchoice and SamSam newly observed values take effect in the registry
on the review date, rather than backdating an unknown effective date. No
unverified EnergyZero legacy value is promoted into a purported pre-2026 tariff.

### Partial verification and export limitations in 2.1.1

The SamSam import/monthly/resolution observation is dated 2026-09-23 in notes.
Its `last_verified` remains 2026-07-02: setting it to the observation date would
incorrectly report the entire record, including unverified export, as current.
The official source identifies the confirmed fields, not every retained field.
Vattenfall retains its single secondary legacy record, all amounts and its old
verification date. Its observation date is not used as a tariff validity boundary.

EnerPrice models export fees as a flat per-kWh deduction. easyEnergy's
[tariff sheet](https://www.easyenergy.com/media/nsfhjtjd/tarievenblad.pdf)
describes charging the purchase fee on the monthly balance of consumption and
export. That netting cannot be represented by a single interval export fee.
The legacy EUR 0.0218 export value is therefore not newly certified, set to zero,
or inferred from the import fee. No additional feed-in costs does not establish
the value of `purchase_fee_export`. Compare export estimates with your own
contract; this patch does not implement billing or saldering logic.

All other unverified amounts and dates remain unchanged. EnergyZero's import
fee stays EUR 0.028 excluding VAT (EUR 0.03388 at 21%), while its export VAT flag
remains independent. Zonnebonus is not added to Zonneplan's fee. The custom
supplier, legacy fallback file and automatic release workflow are unchanged.

## Remote registry core (PR1)

The bundled registry remains installed and usable without network access.
`registry/supplier_tariffs.json` publishes the same initial data as a public,
revisioned snapshot. This is a reviewed data distribution mechanism, not live
supplier verification; freshness continues to refer to each tariff's existing
`last_verified`, not the time a file was downloaded.

Precedence is custom user configuration, newer validated cached/remote registry,
bundled registry, then existing legacy fallback. If a remote supplier has no
period covering an interval's local date, the bundled period is tried before
legacy data. Remote custom records are ignored. The existing per-PriceEntry
Europe/Amsterdam date selection and `{time, price}` arrays remain unchanged.

### Startup and storage

Setup warms bundled/legacy files through HA's executor, loads and validates the
local cache, then starts normally. It never waits for a registry HTTP request.
One manager is shared across config entries, separately from the coordinator
map. Local cache initialization and updates share an asyncio lock.

The cache uses Home Assistant `Store`, storage version 1, key
`nl_day_ahead_prices_supplier_registry`, with atomic writes enabled. Nothing is
written to the integration installation directory. It contains the complete
remote envelope (`schema_version`, `revision`, optional `published_at`, country,
currency and suppliers), plus UTC `last_check`, `last_success` and `last_update`.
`last_check` includes failed attempts; `last_success` means a valid response;
`last_update` means an accepted newer revision. Cache writes are read back before
activation because HA Store may log a write error without raising it.

A corrupt/incompatible cache is warned about and ignored. A valid cached revision
4 is immediately used over bundled revision 1; a failed check leaves 4 active.
A newer bundled revision wins over older cache. Legacy bundled format without
an explicit revision means revision 1.

### Checks and activation

`REMOTE_REGISTRY_URL` is the single default URL constant pointing at this
repository's public raw `main/registry/supplier_tariffs.json`. A HA-managed
background task checks independently of electricity-price refreshes. The
`REMOTE_CHECK_INTERVAL` is 24 hours; persisted attempt timestamps avoid repeated
downloads on restart, including after failures. The task is cancelled after the
last entry unloads. PR1 defaults to enabled; an internal enable flag leaves room
for PR2 without introducing a user-facing option now.

HTTP uses HA's shared aiohttp session, a 20-second total timeout and a 1 MiB body
limit. Network/DNS failures, timeouts, HTTP errors, invalid JSON, invalid schema
and storage failures retain local data and do not mark the price coordinator
unavailable. No retries occur inside a check; the next daily check retries.
An unwritable cache prevents activation and may prevent restart throttling;
the in-memory attempt time still throttles the running process.

`schema_version` describes compatibility; `revision` describes data age. Reject
unsupported schemas regardless of revision. Ignore lower and equal revisions
without replacing the active snapshot or cached tariff payload (check timestamps
are still persisted). For a higher revision: fully validate, persist, atomically
swap the process-wide snapshot on the HA event loop, then notify coordinators.
Callbacks clear derived-analysis caches, reconvert existing raw price intervals,
adjust the interval notification schedule, and notify entities without requesting
market data. Readers never see a partly constructed registry. A single lock
serializes concurrent checks across entries.

### Validation and privacy

The strict remote validator rejects the complete candidate on structural errors:
missing suppliers/fields, invalid enums/types/dates/URLs, non-finite or excessive
fees, invalid country/currency, unsupported versions, reversed or overlapping
inclusive periods and duplicate JSON keys. All eleven built-in suppliers are
required. Shared bundled parsing and selection remain backwards compatible.
Limits are +/- EUR 5/kWh (import nonnegative), EUR 0-1000/month, 100 suppliers and
100 periods per supplier. Realistic negative export fees remain valid.

Only public registry data is requested. No supplier selection, HA IDs, entity
data, consumption, location, settings or telemetry are sent. Standard network
metadata such as the source IP is necessarily visible to GitHub. Transport uses
HTTPS and the trusted repository; this PR does not add cryptographic signing or
independent verification of suppliers' commercial claims.

The shared active snapshot follows the integration's existing process-wide
profile API, assuming one Home Assistant instance per process. No config-entry
migration, new entities/services/options, scraping, audit workflow or release is
part of PR1. See [maintainer workflow](../registry/README.md) for publishing a
reviewed higher revision while preserving history and source quality.
