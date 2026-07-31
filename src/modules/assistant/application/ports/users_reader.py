"""Outbound port: the tenant list the proactive jobs sweep.

Auth exposes no listing use case (nothing user-facing ever lists users), so the
adapter reads the users collection directly — legal for an adapter, and this
port keeps the hexagon blind to that."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class UserView:
    user_id: UUID
    tier: str
    language: str
    currency: str
    objective: str | None


class UsersReader(Protocol):
    async def list_users(self, tier: str | None = None) -> tuple[UserView, ...]:
        """Every user (or one tier's). Ordered by language so a sweep that calls
        the model rides one cached system prefix per language, not per user."""
        ...
