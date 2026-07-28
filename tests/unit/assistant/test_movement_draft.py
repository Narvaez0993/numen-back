"""The draft's lifecycle: pending is the only state anything can happen from."""

import pytest

from src.modules.assistant.domain.errors import DraftNotPendingError

from .fakes import draft


def test_confirm_records_the_movement_id() -> None:
    confirmed = draft().confirm("mov-1")
    assert confirmed.status == "confirmed"
    assert confirmed.movement_id == "mov-1"


def test_discard_never_touches_money() -> None:
    discarded = draft().discard()
    assert discarded.status == "discarded"
    assert discarded.movement_id is None


def test_a_settled_draft_cannot_be_confirmed_again() -> None:
    with pytest.raises(DraftNotPendingError):
        draft().confirm("mov-1").confirm("mov-2")


def test_a_settled_draft_cannot_be_discarded() -> None:
    with pytest.raises(DraftNotPendingError):
        draft().discard().discard()


def test_overrides_edit_what_the_user_may_edit() -> None:
    edited = draft().apply_overrides({"amount": 30_000, "description": "Cena"})
    assert edited.amount == 30_000
    assert edited.description == "Cena"
    assert edited.status == "pending"


def test_identity_fields_are_not_overridable() -> None:
    with pytest.raises(ValueError, match="not overridable"):
        draft().apply_overrides({"user_id": "someone-else"})


def test_overrides_demand_a_pending_draft() -> None:
    with pytest.raises(DraftNotPendingError):
        draft().discard().apply_overrides({"amount": 1})
