"""Field rules shared by the create and update use cases.

Keeping them here (instead of inlined per use case) means an account and a card
are validated exactly the same way whichever door they come through.
"""

from typing import cast

from src.modules.accounts.domain.entities.account import (
    ALLOWED_COLORS,
    ALLOWED_KINDS,
    MAX_AMOUNT,
    MAX_NAME_LENGTH,
    MAX_SUB_LENGTH,
    AccountKind,
)
from src.modules.accounts.domain.errors import InvalidAccountError


def clean_name(raw: str) -> str:
    name = raw.strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        raise InvalidAccountError(f"Name must be 1-{MAX_NAME_LENGTH} characters")
    return name


def clean_sub(raw: str) -> str:
    sub = raw.strip()
    if len(sub) > MAX_SUB_LENGTH:
        raise InvalidAccountError(f"Detail must be at most {MAX_SUB_LENGTH} characters")
    return sub


def clean_icon(raw: str, fallback: str) -> str:
    icon = raw.strip()
    if not icon:
        return fallback
    if len(icon) > MAX_NAME_LENGTH:
        raise InvalidAccountError("Icon name is too long")
    return icon


def clean_color(raw: str, fallback: str) -> str:
    color = raw.strip() or fallback
    if color not in ALLOWED_COLORS:
        raise InvalidAccountError(f"Invalid color: {raw}")
    return color


def ensure_kind(raw: str) -> AccountKind:
    if raw not in ALLOWED_KINDS:
        raise InvalidAccountError(f"Invalid account kind: {raw}")
    return cast(AccountKind, raw)


def ensure_amount(value: int, field: str) -> int:
    """Signed amount in minor units (a debit account can be overdrawn)."""
    if abs(value) > MAX_AMOUNT:
        raise InvalidAccountError(f"{field} is out of range")
    return value


def ensure_positive_amount(value: int, field: str) -> int:
    if value < 0:
        raise InvalidAccountError(f"{field} cannot be negative")
    return ensure_amount(value, field)


def ensure_limit(value: int) -> int:
    if value <= 0:
        raise InvalidAccountError("Credit limit must be greater than zero")
    return ensure_amount(value, "Credit limit")


def ensure_day_of_month(value: int, field: str) -> int:
    if not 1 <= value <= 31:
        raise InvalidAccountError(f"{field} must be a day between 1 and 31")
    return value
