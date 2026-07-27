from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

Scope = Literal["global", "category"]

ALLOWED_SCOPES: frozenset[str] = frozenset({"global", "category"})
# A cap of zero is not a cap, it is a delete. Below this there is nothing to measure.
MIN_TARGET = 1
# Sanity bound for money in minor units, same as accounts, movements and subscriptions.
MAX_TARGET = 10**15


@dataclass(frozen=True)
class Budget:
    """A ceiling the **user** chose, standing until they change it.

    This is the entity that makes a daily figure legitimate. Home used to divide the
    month's leftover income by the days remaining and call it "available today" — a
    permission the app had no business granting, and one that grew every day the user
    held back. A cap is the opposite: it comes from the user, it does not move on its
    own, and what it produces is *"do not go past this"*.

    **It is not per month.** One row per `(user, scope, category)`: set it once in July
    and August measures against the same number without the user touching anything —
    which is what the dead "apply to future months" toggle in the client was reaching
    for. `since` records the month the current value was set, so a later feature can
    tell "this cap is from July" without the entity pretending to be a monthly ledger.

    `scope="global"` is the month's ceiling and there is only ever one; `scope="category"`
    is a watch on one category. **They are not additive**: a category cap warns about
    that category, and every expense still counts against the global one.
    """

    id: str
    user_id: UUID
    scope: Scope
    category_id: str | None
    """Required for `category` scope, always `None` for `global`."""
    target: int
    """Positive, in the minor unit of the user's home currency."""
    since: str
    """`YYYY-MM` — the month the current `target` was set in."""
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        scope: Scope,
        category_id: str | None,
        target: int,
        since: str,
        created_at: datetime,
    ) -> "Budget":
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            scope=scope,
            category_id=category_id if scope == "category" else None,
            target=target,
            since=since,
            created_at=created_at,
        )

    def retargeted(self, *, target: int, since: str) -> "Budget":
        """The same cap with a new number, stamped with the month of the change."""
        return Budget(
            id=self.id,
            user_id=self.user_id,
            scope=self.scope,
            category_id=self.category_id,
            target=target,
            since=since,
            created_at=self.created_at,
        )
