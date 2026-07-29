"""A goal as a movement endpoint: transfers only, one end only.

A pocket holds set-aside money — nothing is spent or earned in one directly, and money
never hops pocket-to-pocket. The shape rules are the whole guard: the HTTP schemas
already refuse `goal` refs (only the goals module mints them through its port), so
these tests pin the domain layer that backs that up.
"""

import pytest

from src.modules.movements.domain.entities.movement import Movement, SourceRef
from src.modules.movements.domain.errors import InvalidMovementError
from src.modules.movements.domain.validation import ensure_shape

ACCOUNT = SourceRef(type="account", id="nequi")
POCKET = SourceRef(type="goal", id="viaje")
OTHER_POCKET = SourceRef(type="goal", id="fondo")


def test_a_transfer_can_fill_a_pocket() -> None:
    ensure_shape("transfer", ACCOUNT, POCKET, None)


def test_a_transfer_can_drain_a_pocket() -> None:
    ensure_shape("transfer", POCKET, ACCOUNT, None)


def test_money_never_hops_pocket_to_pocket() -> None:
    with pytest.raises(InvalidMovementError):
        ensure_shape("transfer", POCKET, OTHER_POCKET, None)


def test_nothing_is_spent_from_a_pocket_directly() -> None:
    with pytest.raises(InvalidMovementError):
        ensure_shape("expense", POCKET, None, None)


def test_income_never_lands_in_a_pocket() -> None:
    with pytest.raises(InvalidMovementError):
        ensure_shape("income", POCKET, None, None)


def test_the_deltas_treat_the_pocket_like_any_endpoint() -> None:
    """The cash-basis rule stays one rule: -amount at the source, +amount at the
    destination. The pocket's leg of the ledger is a no-op, but the ACCOUNT leg is
    what makes the balance really move."""
    from datetime import UTC, datetime
    from uuid import uuid4

    contribution = Movement(
        id="m1",
        user_id=uuid4(),
        type="transfer",
        description="Viaje a Japón",
        amount=500_000,
        currency="COP",
        source=ACCOUNT,
        destination=POCKET,
        category_id=None,
        occurred_on="2026-07-27",
        captured_via="manual",
        created_at=datetime.now(UTC),
    )

    assert contribution.deltas() == ((ACCOUNT, -500_000), (POCKET, 500_000))
    assert contribution.reverted_deltas() == ((ACCOUNT, 500_000), (POCKET, -500_000))
