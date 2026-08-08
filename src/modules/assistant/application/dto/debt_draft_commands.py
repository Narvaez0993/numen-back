from uuid import UUID

from pydantic import BaseModel

from src.modules.assistant.application.dto.debt_draft import DebtDraftDTO


class ConfirmDebtDraftInputDTO(BaseModel):
    """The card's answers; `None` means keep what the agent staged.

    `clear_account` exists because `None` cannot mean two things: leaving the field
    alone and answering "no money moved" are different, and the second is a real
    answer for a dinner split.
    """

    user_id: UUID
    draft_id: str
    today: str
    target_debt_id: str | None = None
    """Which debt the abono pays down, when the card had to ask."""
    direction: str | None = None
    counterparty_id: str | None = None
    counterparty_name: str | None = None
    amount: int | None = None
    account_id: str | None = None
    clear_account: bool = False
    due_on: str | None = None
    note: str | None = None


class DiscardDebtDraftInputDTO(BaseModel):
    user_id: UUID
    draft_id: str


class ConfirmDebtDraftOutputDTO(BaseModel):
    """What was created, in the shape undo needs.

    A NEW debt is undone by deleting the debt (which reverts its loan transfer with
    it). An ABONO is undone by deleting the movement that carried it — the debt must
    survive. So `movement_id` is set only on a payment, and that is the flag telling
    the caller which of the two undos applies.
    """

    draft: DebtDraftDTO
    debt_id: str
    movement_id: str | None = None


class DiscardDebtDraftOutputDTO(BaseModel):
    draft: DebtDraftDTO
