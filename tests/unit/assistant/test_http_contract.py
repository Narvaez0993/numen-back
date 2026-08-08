"""The HTTP schemas carry everything the DTOs do.

FastAPI's `response_model` does not just document a shape, it ENFORCES it: any field
the schema fails to declare is silently stripped from the JSON. No error, no warning
— the client simply never hears about it.

That shipped. `DebtDraftDTO` grew `kind` and `target_debt_id`, `DebtDraftResponse` did
not, and the app rendered every repayment as a brand-new loan: "TE DEBEN" instead of
"ABONO", "¿de qué cuenta salió?" over money that was landing, and a "no movió plata"
option that cannot mean anything for a repayment. The backend was right the whole
time; the field never made it across the wire.

These tests compare the two field sets so the next added field cannot go missing.
"""

from pydantic import BaseModel

from src.modules.assistant.adapters.inbound.http.schemas import (
    DebtDraftResponse,
    DraftResponse,
)
from src.modules.assistant.application.dto.debt_draft import DebtDraftDTO
from src.modules.assistant.application.dto.draft import DraftDTO


def _fields(model: type[BaseModel]) -> set[str]:
    return set(model.model_fields)


def test_the_debt_draft_response_carries_every_dto_field() -> None:
    assert _fields(DebtDraftDTO) == _fields(DebtDraftResponse)


def test_the_movement_draft_response_carries_every_dto_field() -> None:
    assert _fields(DraftDTO) == _fields(DraftResponse)
