from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID, uuid4

DEFAULT_CARD_ICON = "credit-card"
DEFAULT_CARD_COLOR = "coral"


@dataclass(frozen=True)
class CreditCard:
    """A credit card: a liability, so it is its own entity — not an `Account`.

    `debt` is what is owed right now in the minor unit of `currency`, and
    `initial_debt` anchors it the same way `Account.initial_balance` does
    (`debt == initial_debt + Σ charges - Σ payments`). `debt` may exceed `limit`:
    real cards do, and a charge must never be rejected by our bookkeeping —
    going over the limit is something to *flag*, not to forbid.

    `cutoff_day` and `due_day` are days of the month (1-31), never display
    strings: the client renders them localized.
    """

    id: str
    user_id: UUID
    name: str
    icon: str
    color: str
    currency: str
    debt: int
    initial_debt: int
    limit: int
    cutoff_day: int
    due_day: int | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        name: str,
        icon: str,
        color: str,
        currency: str,
        debt: int,
        limit: int,
        cutoff_day: int,
        due_day: int | None,
        created_at: datetime,
    ) -> "CreditCard":
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            icon=icon,
            color=color,
            currency=currency,
            debt=debt,
            initial_debt=debt,
            limit=limit,
            cutoff_day=cutoff_day,
            due_day=due_day,
            created_at=created_at,
        )

    def with_updates(
        self,
        *,
        name: str | None = None,
        icon: str | None = None,
        color: str | None = None,
        debt: int | None = None,
        limit: int | None = None,
        cutoff_day: int | None = None,
        due_day: int | None = None,
    ) -> "CreditCard":
        new_debt = self.debt if debt is None else debt
        return replace(
            self,
            name=self.name if name is None else name,
            icon=self.icon if icon is None else icon,
            color=self.color if color is None else color,
            debt=new_debt,
            initial_debt=self.initial_debt + (new_debt - self.debt),
            limit=self.limit if limit is None else limit,
            cutoff_day=self.cutoff_day if cutoff_day is None else cutoff_day,
            due_day=self.due_day if due_day is None else due_day,
        )
