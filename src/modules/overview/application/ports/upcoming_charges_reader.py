from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class UpcomingChargeView:
    """A recurring charge Home announces. References only, like everything else in
    the payload: the client resolves the name and icon from its own catalog."""

    subscription_id: str
    charge_on: str
    amount: int
    status: str
    charge_id: str | None


class UpcomingChargesReader(Protocol):
    """Outbound port: what is about to be charged in the next few days.

    `overview` re-declares the shape it needs instead of importing `subscriptions` —
    the same anti-corruption seam it uses for balances and movement summaries.
    """

    async def upcoming(
        self, user_id: UUID, date_from: str, date_to: str, limit: int
    ) -> list[UpcomingChargeView]: ...
