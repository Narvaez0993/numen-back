"""The plays — moves the agent proposes that materialize as real objects.

Create-vs-update is decided AT GENERATION: `raise_category_cap` carries the
`budget_id` it will update; `set_*` carries what it will create. The apply
endpoint only dispatches. `treat` carries no button: it is the agent saying
"this fits — enjoy it", verified by the domain's slack math.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from src.modules.assistant.domain.entities.agent_output import Play

MAX_PLAY_TEXT = 200


class _PlayBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str = Field(max_length=MAX_PLAY_TEXT)
    status: str
    result_id: str | None = None
    failure_code: str | None = None


class SetCategoryCapPlayDTO(_PlayBase):
    action: Literal["set_category_cap"]
    category_id: str
    category_name: str
    target: int
    linked_goal_id: str | None = None


class RaiseCategoryCapPlayDTO(_PlayBase):
    action: Literal["raise_category_cap"]
    budget_id: str
    category_id: str
    category_name: str
    current_target: int
    target: int


class SetMonthCapPlayDTO(_PlayBase):
    action: Literal["set_month_cap"]
    target: int


class ContributeGoalPlayDTO(_PlayBase):
    action: Literal["contribute_goal"]
    goal_id: str
    goal_name: str
    amount: int


class TreatPlayDTO(_PlayBase):
    action: Literal["treat"]
    amount: int


PlayDTO = Annotated[
    SetCategoryCapPlayDTO
    | RaiseCategoryCapPlayDTO
    | SetMonthCapPlayDTO
    | ContributeGoalPlayDTO
    | TreatPlayDTO,
    Field(discriminator="action"),
]

PLAY_ADAPTER: TypeAdapter[PlayDTO] = TypeAdapter(PlayDTO)

_LIFECYCLE_FIELDS = frozenset({"id", "action", "text", "status", "result_id", "failure_code"})


def play_dto_from_domain(play: Play) -> PlayDTO:
    return PLAY_ADAPTER.validate_python(
        {
            "id": play.id,
            "action": play.action,
            "text": play.text,
            "status": play.status,
            "result_id": play.result_id,
            "failure_code": play.failure_code,
            **dict(play.params),
        }
    )


def params_of(dto: PlayDTO) -> dict[str, Any]:
    """The action-specific fields — what the domain `Play` stores as `params`."""
    return {k: v for k, v in dto.model_dump().items() if k not in _LIFECYCLE_FIELDS}
