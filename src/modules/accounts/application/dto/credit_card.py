from pydantic import BaseModel

from src.modules.accounts.domain.entities.credit_card import CreditCard


class CreditCardDTO(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    currency: str
    debt: int
    limit: int
    cutoff_day: int
    due_day: int | None

    @classmethod
    def from_domain(cls, card: CreditCard) -> "CreditCardDTO":
        return cls(
            id=card.id,
            name=card.name,
            icon=card.icon,
            color=card.color,
            currency=card.currency,
            debt=card.debt,
            limit=card.limit,
            cutoff_day=card.cutoff_day,
            due_day=card.due_day,
        )
