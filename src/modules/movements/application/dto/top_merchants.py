from uuid import UUID

from pydantic import BaseModel

from src.modules.movements.application.ports.movement_repository import MerchantSpend


class TopMerchantsInputDTO(BaseModel):
    """`category_id: null` is the unclassified bucket, not "every category"."""

    user_id: UUID
    date_from: str
    date_to: str
    category_id: str | None = None
    limit: int = 5


class OverallTopMerchantsInputDTO(BaseModel):
    """The whole period, category-blind — no `category_id` to mis-read."""

    user_id: UUID
    date_from: str
    date_to: str
    limit: int = 5


class MerchantSpendDTO(BaseModel):
    label: str
    spent: int
    count: int

    @classmethod
    def from_domain(cls, merchant: MerchantSpend) -> "MerchantSpendDTO":
        return cls(label=merchant.label, spent=merchant.spent, count=merchant.count)


class TopMerchantsOutputDTO(BaseModel):
    """Where a category's money went, biggest first. Amounts in the minor unit of the
    user's currency."""

    date_from: str
    date_to: str
    merchants: list[MerchantSpendDTO]
