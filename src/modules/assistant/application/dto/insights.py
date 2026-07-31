"""Rule insights — computed on read, never persisted, never through the LLM.

The server ships data plus a deterministic `key`; the client owns the copy
(i18n). The key carries the period, so a dismissal naturally expires when the
thing it silenced stops existing ("cap:comida:2026-08" dies with August).
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class CapAlertInsight(BaseModel):
    """A budget cap at ≥80% — or already broken."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["cap_alert"]
    key: str
    scope: Literal["global", "category"]
    category_id: str | None
    category_name: str | None
    used: float
    """`spent / target`, unclamped — >1 means broken."""
    target: int
    spent: int
    over: int | None


class UpcomingChargeInsight(BaseModel):
    """A subscription charge landing within the next two days."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["upcoming_charge"]
    key: str
    subscription_id: str
    name: str
    amount: int
    due_on: str
    charge_id: str | None
    """Present when the charge is already `pending` (confirm/skip act on it)."""


class UncategorizedInsight(BaseModel):
    """Enough unclassified movements this month to be worth a sweep."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["uncategorized"]
    key: str
    count: int
    spent: int


InsightDTO = Annotated[
    CapAlertInsight | UpcomingChargeInsight | UncategorizedInsight,
    Field(discriminator="kind"),
]
