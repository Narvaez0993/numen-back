from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

MAX_EVENT_NAME_LENGTH = 60


@dataclass(frozen=True)
class SharedEvent:
    """A split moment — the dinner, the trip — that groups the debts born from it.

    It carries **no money logic**: the split happened once, at creation, and produced
    plain debts. `total` is what the whole thing cost (the user's own share included),
    kept so the card can say "Cena del viernes · $400.000 entre 4"; the sum that is
    still owed lives in the debts.
    """

    id: str
    user_id: UUID
    name: str
    total: int
    occurred_on: str
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        name: str,
        total: int,
        occurred_on: str,
        created_at: datetime,
    ) -> "SharedEvent":
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            total=total,
            occurred_on=occurred_on,
            created_at=created_at,
        )
