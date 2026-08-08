from uuid import UUID

from pydantic import BaseModel

from src.modules.movements.application.ports.movement_repository import DebtTransfer


class DebtTransfersInputDTO(BaseModel):
    user_id: UUID


class DebtTransferDTO(BaseModel):
    debt_id: str
    movement_id: str
    amount: int
    occurred_on: str
    description: str
    into_debt: bool
    movement_type: str

    @classmethod
    def from_domain(cls, transfer: DebtTransfer) -> "DebtTransferDTO":
        return cls(
            debt_id=transfer.debt_id,
            movement_id=transfer.movement_id,
            amount=transfer.amount,
            occurred_on=transfer.occurred_on,
            description=transfer.description,
            into_debt=transfer.into_debt,
            movement_type=transfer.movement_type,
        )


class DebtTransfersOutputDTO(BaseModel):
    """Every movement that crossed between an account and a debt, oldest first."""

    transfers: list[DebtTransferDTO]
