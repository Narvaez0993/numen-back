from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.modules.debts.application.ports.counterparty_repository import (
    CounterpartyRepository,
)
from src.modules.debts.domain.entities.counterparty import Counterparty
from src.modules.debts.domain.errors import CounterpartyNotFoundError, InvalidDebtError
from src.modules.debts.domain.validation import ensure_person_name


@dataclass
class CounterpartyResolver:
    """Turns "who" into a person: an existing id, or a name that creates one inline.

    Shared by the one-on-one create and the event split, so both spell the rule the
    same way: an id must exist, a name is normalized and de-duped ("juan" reuses
    "Juan" instead of minting a twin — the unique index on the normalized key backs
    this up in the store).
    """

    counterparty_repository: CounterpartyRepository

    async def resolve(
        self,
        user_id: UUID,
        *,
        counterparty_id: str | None,
        counterparty_name: str | None,
    ) -> Counterparty:
        if counterparty_id is not None:
            existing = await self.counterparty_repository.find(user_id, counterparty_id)
            if existing is None:
                raise CounterpartyNotFoundError()
            return existing

        if counterparty_name is None:
            raise InvalidDebtError("A debt needs a person: an id or a name")

        name = ensure_person_name(counterparty_name)
        known = await self.counterparty_repository.find_by_name(user_id, name)
        if known is not None:
            return known

        counterparty = Counterparty.create(user_id=user_id, name=name, created_at=datetime.now(UTC))
        await self.counterparty_repository.save(counterparty)
        return counterparty
