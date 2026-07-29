"""Field rules for a debt, shared by create and update.

Small and boring on purpose — the interesting rules (overpaying, split sums) live with
the operations that can break them.
"""

from datetime import date
from typing import cast

from src.modules.debts.domain.entities.counterparty import MAX_NAME_LENGTH
from src.modules.debts.domain.entities.debt import (
    ALLOWED_DIRECTIONS,
    MAX_AMOUNT,
    MAX_NOTE_LENGTH,
    Direction,
)
from src.modules.debts.domain.errors import InvalidDebtError


def ensure_direction(raw: str) -> Direction:
    if raw not in ALLOWED_DIRECTIONS:
        raise InvalidDebtError(f"Invalid direction: {raw}")
    return cast(Direction, raw)


def ensure_amount(amount: int) -> int:
    if not 0 < amount <= MAX_AMOUNT:
        raise InvalidDebtError("A debt has to be a positive amount")
    return amount


def ensure_due_on(raw: str | None) -> str | None:
    """`YYYY-MM-DD` or nothing. The past is allowed — registering a debt that is
    already overdue is a real case, not an error."""
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise InvalidDebtError(f"Invalid due date: {raw} (expected YYYY-MM-DD)") from exc


def ensure_note(raw: str | None) -> str | None:
    if raw is None:
        return None
    note = raw.strip()
    if not note:
        return None
    if len(note) > MAX_NOTE_LENGTH:
        raise InvalidDebtError(f"Note must be at most {MAX_NOTE_LENGTH} characters")
    return note


def ensure_person_name(raw: str) -> str:
    name = " ".join(raw.split())
    if not name or len(name) > MAX_NAME_LENGTH:
        raise InvalidDebtError(f"Person name must be 1-{MAX_NAME_LENGTH} characters")
    return name
