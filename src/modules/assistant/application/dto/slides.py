"""El Corte's slides — one discriminated union, one source of truth.

Unlike chat blocks there is no second "hydrated" union: a slide is a frozen
snapshot of a closed month (numbers baked, narration baked). The only living
reference, `PlaySlide.play_id`, points inside the same output's `plays`, which
travels in the same response — the client resolves it locally.

Names are denormalized on purpose: if the category is deleted in October, the
July Corte neither lies nor breaks.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

MAX_SLIDE_TEXT = 180


class CoverSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["cover"]
    id: str
    text: str = Field(max_length=MAX_SLIDE_TEXT)


class BigNumberSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["big_number"]
    id: str
    amount: int
    count: int
    text: str = Field(max_length=MAX_SLIDE_TEXT)


class CategoryBar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: str
    name: str
    amount: int
    pct: float
    """Fraction of the month's expense total, 0..1."""


class CategoryBarsSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["category_bars"]
    id: str
    bars: list[CategoryBar] = Field(min_length=1, max_length=3)
    text: str = Field(max_length=MAX_SLIDE_TEXT)


class FunFactSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["fun_fact"]
    id: str
    day: str
    """`YYYY-MM-DD` — the client names the weekday in the user's language."""
    amount: int
    count: int
    text: str = Field(max_length=MAX_SLIDE_TEXT)


class PulseSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["pulse"]
    id: str
    current: int
    previous: int
    delta_pct: float
    """Signed fraction vs the same span of the previous month (-0.08 = 8% less)."""
    text: str = Field(max_length=MAX_SLIDE_TEXT)


class GoalSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["goal"]
    id: str
    goal_id: str
    name: str
    saved: int
    target: int
    pct: float
    needed_per_month: int | None
    """Goals' own pace math (per month to land on the date); None without a date."""
    text: str = Field(max_length=MAX_SLIDE_TEXT)


class FirstMonthSlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["first_month"]
    id: str
    text: str = Field(max_length=MAX_SLIDE_TEXT)


class PlaySlide(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["play"]
    id: str
    play_id: str
    text: str = Field(max_length=MAX_SLIDE_TEXT)


Slide = Annotated[
    CoverSlide
    | BigNumberSlide
    | CategoryBarsSlide
    | FunFactSlide
    | PulseSlide
    | GoalSlide
    | FirstMonthSlide
    | PlaySlide,
    Field(discriminator="type"),
]

SLIDES_ADAPTER: TypeAdapter[list[Slide]] = TypeAdapter(list[Slide])
