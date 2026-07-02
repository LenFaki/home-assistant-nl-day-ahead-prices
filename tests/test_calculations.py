from datetime import datetime, timezone

from custom_components.nl_day_ahead_prices.models import (
    PriceEntry,
    calculate_all_in_price,
    convert_to_eur_kwh,
    next_hour_price,
)


def test_convert_eur_mwh_to_eur_kwh() -> None:
    assert convert_to_eur_kwh(123.45, "EUR/MWh") == 0.12345


def test_convert_eur_kwh_is_unchanged() -> None:
    assert convert_to_eur_kwh(0.234, "EUR/kWh") == 0.234


def test_all_in_formula() -> None:
    assert calculate_all_in_price(0.1, 0.1108, 0.01653, 0.21) == 0.2308013


def test_next_hour_all_in_formula_example() -> None:
    market_price = 0.001
    energy_tax_incl_vat = 0.1108
    supplier_markup_excl_vat = 0.0152
    vat = 0.21

    assert calculate_all_in_price(
        market_price,
        energy_tax_incl_vat,
        supplier_markup_excl_vat,
        vat,
    ) == 0.130192


def test_next_hour_price_uses_next_full_hour_entry() -> None:
    prices = [
        PriceEntry(datetime(2026, 7, 2, 10, tzinfo=timezone.utc), 0.10),
        PriceEntry(datetime(2026, 7, 2, 11, tzinfo=timezone.utc), 0.20),
    ]

    assert next_hour_price(prices, datetime(2026, 7, 2, 10, 12, tzinfo=timezone.utc)) == 0.20
