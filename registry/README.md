# EnerPrice remote supplier registry

This directory publishes static public tariff data for the remote-registry core.
It is not a live supplier scraper. Initial revision 1 exactly copies the v2.1.1
bundled supplier data, including historical periods and conservative provenance.
The integration version remains unchanged for this infrastructure PR.

## Schema and revisions

- `schema_version: 1` identifies the compatible data format. Change it only for
  incompatible format changes, together with integration support.
- `revision` is a positive integer identifying a complete data snapshot. Increase
  it for every verified data change, independently of integration releases.
- Optional `published_at` is an explicit UTC ISO-8601 publication timestamp.
  It is not a supplier verification date or contract effective date.
- `country: NL` and `currency: EUR` are fixed. Fees use EUR/kWh and EUR/month.
- `supplier_tariffs.schema.json` describes structural requirements. Runtime
  validation additionally checks period ordering, overlap, finite numbers and
  source URL semantics. Use the runtime validator as the final authority.

All eleven built-in commercial supplier IDs must be present. A custom entry may
be included for compatibility but remote custom values are never selected.
User custom configuration always has precedence.

## Safety bounds

The downloader accepts at most 1 MiB, including streamed/decompressed data, with
a 20-second total timeout. It does not follow redirects. The registry allows
at most 100 suppliers and 100 tariff periods per supplier. Supplier names are
limited to 200 characters, source URLs to 2048 and notes to 10000.

Per-kWh fees must be finite and between -5 and +5 EUR/kWh; import fees must also
be nonnegative. Monthly fees must be between 0 and 1000 EUR inclusive. These
deliberately broad limits catch obvious decimal/unit mistakes, not market moves.
Negative export fees are supported. Booleans cannot substitute for numbers.

## Safe maintainer workflow

1. Verify a supplier's actual tariff against a primary source and its contract
   scope. Establish the effective date before introducing a validity boundary;
   a website observation date alone is not an effective date.
2. Edit `registry/supplier_tariffs.json`, keeping amounts and VAT flags precise.
3. Preserve historical periods; endpoints are inclusive and may not overlap.
4. Update source/provenance notes. Do not promote secondary values to official
   or advance the complete-record verification date after a partial check.
5. Increment `revision` and set `published_at` to the actual UTC publication time.
6. Run the complete test suite and Ruff. Validate the candidate locally:

   ```bash
   python -c 'from pathlib import Path; from custom_components.nl_day_ahead_prices.remote_registry import decode_registry, parse_remote_registry; parse_remote_registry(decode_registry(Path("registry/supplier_tariffs.json").read_bytes()))'
   pytest
   ruff check .
   ```

7. Review and merge the data change. No integration version bump is necessary
   for a remote-only data update; the existing release pipeline is unchanged.
8. Installations with this core receive newer compatible revisions at their next
   scheduled check, normally within 24 hours. Offline installations retain local
   data until a later successful check.

To revert erroneous data, publish corrected data under a **higher** revision.
Do not decrement the revision or edit content under an already published one.
When refreshing the bundled file in a future integration release, include its
matching `revision`; older bundled files without that field mean revision 1.
Do not renumber an unchanged bundled snapshot.

See [runtime architecture](../docs/supplier-tariff-registry.md#remote-registry-core-pr1)
for startup, storage, fallback and privacy behavior. PR2 provides per-entry
Automatic/Bundled-only options and diagnostic entities. PR3 supplier auditing
is intentionally absent.
