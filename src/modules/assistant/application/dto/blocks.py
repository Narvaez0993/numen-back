"""The block contract — the single source of truth for what the agent can say.

One discriminated union feeds everything: the JSON Schema handed to the model as
the `respond_with_blocks` tool, the validation of what it answers, the shape
persisted in chat history, and the HTTP response schema. Defining blocks once is
what keeps the four from drifting.

Two unions on purpose: the model emits (and history stores) `DraftRefBlock` — a
draft **reference**, never its numbers — and responses hydrate it into
`DraftBlock` with the draft's current state, so history always shows what became
of a draft without duplicating money fields.
"""

from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from src.modules.assistant.application.dto.debt_draft import DebtDraftDTO
from src.modules.assistant.application.dto.draft import DraftDTO

# The only places a navigate chip may point at. Expo-router routes that exist
# today; the client keeps the typed twin. The model inventing URLs is not a
# style problem, it is a phishing surface — hence allowlist, not convention.
NAVIGATE_ROUTES: Final[tuple[str, ...]] = (
    "/accounts",
    "/budgets",
    "/categories",
    "/deudas",
    "/goals",
    "/movements",
    "/plan",
    "/profile",
    "/subscriptions",
)

MAX_BLOCKS_PER_MESSAGE = 12


class TextBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["text"]
    text: str = Field(min_length=1, max_length=2000)


class StatBlock(BaseModel):
    """A labelled figure. `value` is display-ready text; `amount` (minor units)
    and `pct` let the client reformat with the user's locale when present."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["stat"]
    label: str = Field(min_length=1, max_length=60)
    value: str = Field(min_length=1, max_length=40)
    amount: int | None = None
    pct: float | None = None


class ChartPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=24)
    value: int


class ChartBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["chart"]
    kind: Literal["bars", "line"]
    title: str = Field(min_length=1, max_length=80)
    points: list[ChartPoint] = Field(min_length=1, max_length=24)


class NavigateBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["navigate"]
    label: str = Field(min_length=1, max_length=60)
    route: str

    @field_validator("route")
    @classmethod
    def route_must_be_allowed(cls, route: str) -> str:
        if route not in NAVIGATE_ROUTES:
            raise ValueError(f"Route not allowed: {route}")
        return route


class DraftRefBlock(BaseModel):
    """What the model emits and history stores: the draft id, nothing else."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["draft"]
    draft_id: str = Field(min_length=1, max_length=64)


class DebtDraftRefBlock(BaseModel):
    """The debt twin of `DraftRefBlock`. Its own type rather than a flag on that
    one: the card it renders asks different questions — which person, which account
    — and a client switching on `type` should not have to guess which."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["debt_draft"]
    debt_draft_id: str = Field(min_length=1, max_length=64)


LlmBlock = Annotated[
    TextBlock | StatBlock | ChartBlock | NavigateBlock | DraftRefBlock | DebtDraftRefBlock,
    Field(discriminator="type"),
]

LLM_BLOCKS_ADAPTER: TypeAdapter[list[LlmBlock]] = TypeAdapter(list[LlmBlock])


class RespondWithBlocksInput(BaseModel):
    """The terminal tool's arguments — also the schema the model is given."""

    model_config = ConfigDict(extra="forbid")

    blocks: list[LlmBlock] = Field(min_length=1, max_length=MAX_BLOCKS_PER_MESSAGE)


class DraftBlock(BaseModel):
    """The hydrated twin of `DraftRefBlock` — HTTP responses only."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["draft"]
    draft: DraftDTO


class DebtDraftBlock(BaseModel):
    """The hydrated twin of `DebtDraftRefBlock` — HTTP responses only."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["debt_draft"]
    debt_draft: DebtDraftDTO


ApiBlock = Annotated[
    TextBlock | StatBlock | ChartBlock | NavigateBlock | DraftBlock | DebtDraftBlock,
    Field(discriminator="type"),
]
