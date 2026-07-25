from uuid import UUID

from pydantic import BaseModel

from src.modules.movements.application.dto.movement import MovementDTO


class ListMovementsInputDTO(BaseModel):
    user_id: UUID
    date_from: str | None = None
    date_to: str | None = None
    type: str | None = None
    source_id: str | None = None
    category_id: str | None = None
    limit: int = 100


class ListMovementsOutputDTO(BaseModel):
    movements: list[MovementDTO]
