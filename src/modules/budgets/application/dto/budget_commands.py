from uuid import UUID

from pydantic import BaseModel


class CreateBudgetInputDTO(BaseModel):
    """`tier` gates the number of category caps; `today` stamps the month the cap was
    set in. Neither comes from the request body."""

    user_id: UUID
    tier: str
    today: str
    scope: str
    category_id: str | None = None
    target: int


class UpdateBudgetInputDTO(BaseModel):
    """Only the number can change: moving a cap from one category to another is
    deleting one and creating the other."""

    user_id: UUID
    today: str
    budget_id: str
    target: int


class DeleteBudgetInputDTO(BaseModel):
    user_id: UUID
    budget_id: str


class BudgetsSnapshotInputDTO(BaseModel):
    user_id: UUID
    currency: str
    today: str


class GlobalCapInputDTO(BaseModel):
    """What Home asks for: the global cap only, no category work."""

    user_id: UUID
    today: str


class CategoryCapsInputDTO(BaseModel):
    """The other half of what Home asks for: the caps of the categories it lists,
    measured but without their merchants."""

    user_id: UUID
    today: str
