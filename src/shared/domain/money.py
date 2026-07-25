"""Currency metadata shared by every module that stores money.

Amounts are **integers in the currency's minor unit** (USD cents, COP pesos) —
never floats. This module is the single place that knows the exponent per
currency: supporting a new one is one entry here (and its twin in the client's
`MINOR_UNIT_EXPONENT` table).
"""

from typing import Final

_MINOR_UNIT_EXPONENTS: Final[dict[str, int]] = {
    "COP": 0,
    "USD": 2,
    "EUR": 2,
    "MXN": 2,
}

SUPPORTED_CURRENCIES: Final[tuple[str, ...]] = tuple(_MINOR_UNIT_EXPONENTS)

DEFAULT_CURRENCY: Final[str] = "USD"


def is_supported_currency(code: str) -> bool:
    return code in _MINOR_UNIT_EXPONENTS


def minor_unit_exponent(code: str) -> int:
    """Digits after the decimal point for `code` (ISO 4217 minor unit)."""
    try:
        return _MINOR_UNIT_EXPONENTS[code]
    except KeyError as exc:
        raise ValueError(f"Unsupported currency: {code}") from exc
