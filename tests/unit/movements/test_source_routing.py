"""Which leg of the ledger a reference is sent to.

The bug this file exists to prevent shipped once, and the unit suite was green the
whole time: every use-case test fakes the ledger, so nothing checked that a REAL
`debt` ref reaches a leg that knows how to resolve it. It did not — the router sent
"goal here, everything else to accounts", so a claim was looked up as an account,
found nothing, and the API answered `movements.source_not_found`: a true error
message about the wrong thing.

The lesson is the assertion: routing is a table, and every endpoint kind has a row.
"""

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from src.modules.movements.adapters.outbound.ledger.routing_source_ledger import (
    RoutingSourceLedger,
)
from src.modules.movements.application.ports.source_ledger import SourceSnapshot
from src.modules.movements.domain.entities.movement import SourceRef


@dataclass
class SpyLeg:
    """Answers for anything, and remembers it was the one asked."""

    name: str

    def __post_init__(self) -> None:
        self.asked: list[SourceRef] = []
        self.moved: list[tuple[SourceRef, int]] = []

    async def find(self, user_id: UUID, ref: SourceRef) -> SourceSnapshot | None:
        self.asked.append(ref)
        return SourceSnapshot(ref=ref, type=ref.type, currency="COP")

    async def apply_delta(self, user_id: UUID, ref: SourceRef, delta: int) -> None:
        self.moved.append((ref, delta))


def _router() -> tuple[RoutingSourceLedger, SpyLeg, SpyLeg, SpyLeg]:
    accounts, goals, debts = SpyLeg("accounts"), SpyLeg("goals"), SpyLeg("debts")
    return (
        RoutingSourceLedger(accounts=accounts, goals=goals, debts=debts),  # type: ignore[arg-type]
        accounts,
        goals,
        debts,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source_type", "expected"),
    [("account", "accounts"), ("credit_card", "accounts"), ("goal", "goals"), ("debt", "debts")],
)
async def test_every_endpoint_kind_reaches_the_leg_that_can_resolve_it(
    source_type: str, expected: str
) -> None:
    router, accounts, goals, debts = _router()
    legs = {"accounts": accounts, "goals": goals, "debts": debts}

    await router.find(uuid4(), SourceRef(type=source_type, id="x"))  # type: ignore[arg-type]

    assert legs[expected].asked, f"{source_type} never reached the {expected} leg"
    for name, leg in legs.items():
        if name != expected:
            assert not leg.asked, f"{source_type} wrongly reached the {name} leg"


@pytest.mark.asyncio
async def test_a_claim_is_not_looked_up_as_an_account() -> None:
    """The exact shape of the shipped bug: lending 50.000 created the debt, then the
    transfer went looking for an ACCOUNT with the debt's id and 404'd — with a fresh
    uuid every retry, because each attempt minted a new debt first."""
    router, accounts, _, debts = _router()

    await router.find(uuid4(), SourceRef(type="debt", id="claim-1"))

    assert [ref.id for ref in debts.asked] == ["claim-1"]
    assert accounts.asked == []


@pytest.mark.asyncio
async def test_the_delta_follows_the_same_table() -> None:
    """Finding on one leg and moving on another would debit the wrong ledger."""
    router, accounts, _, debts = _router()

    await router.apply_delta(uuid4(), SourceRef(type="debt", id="claim-1"), -50_000)

    assert debts.moved == [(SourceRef(type="debt", id="claim-1"), -50_000)]
    assert accounts.moved == []
