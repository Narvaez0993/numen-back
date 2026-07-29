"""`to_minor_units` — the one place major-unit amounts become stored integers."""

from decimal import Decimal

import pytest

from src.shared.domain.money import to_minor_units


def test_cop_has_no_decimals() -> None:
    assert to_minor_units("25000", "COP") == 25000


def test_usd_scales_to_cents() -> None:
    assert to_minor_units("12.50", "USD") == 1250


def test_whole_usd_amount_scales_too() -> None:
    assert to_minor_units(Decimal("450"), "USD") == 45000


def test_rounds_half_up() -> None:
    assert to_minor_units("12.505", "USD") == 1251


def test_extra_precision_rounds_away() -> None:
    assert to_minor_units("0.999", "COP") == 1


def test_zero_is_fine() -> None:
    assert to_minor_units("0", "USD") == 0


def test_negative_amount_is_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        to_minor_units("-1", "COP")


def test_garbage_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid amount"):
        to_minor_units("veinticinco", "COP")


def test_nan_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid amount"):
        to_minor_units("NaN", "COP")


def test_unsupported_currency_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported currency"):
        to_minor_units("10", "GBP")
