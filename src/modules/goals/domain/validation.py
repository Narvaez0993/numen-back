"""Field rules for a goal, shared by create and update."""

from datetime import date

from src.modules.goals.domain.entities.goal import MAX_NAME_LENGTH, MAX_TARGET, MIN_TARGET
from src.modules.goals.domain.errors import InvalidGoalError


def ensure_name(raw: str) -> str:
    name = " ".join(raw.split())
    if not name or len(name) > MAX_NAME_LENGTH:
        raise InvalidGoalError(f"Goal name must be 1-{MAX_NAME_LENGTH} characters")
    return name


def ensure_target(target: int) -> int:
    if not MIN_TARGET <= target <= MAX_TARGET:
        raise InvalidGoalError("A goal has to be a positive amount")
    return target


def ensure_target_date(raw: str | None) -> str | None:
    """`YYYY-MM-DD` or nothing. The past is rejected at creation time only by common
    sense in the client; here a date just has to be a date — editing an old goal must
    not explode on a deadline that already went by."""
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise InvalidGoalError(f"Invalid target date: {raw} (expected YYYY-MM-DD)") from exc


def ensure_amount(amount: int) -> int:
    if not 0 < amount <= MAX_TARGET:
        raise InvalidGoalError("The amount has to be positive")
    return amount
