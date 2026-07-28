from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CategoryView:
    id: str
    name: str
    flow: str
    """`expense` | `income` — a draft's category must match its type."""


class CategoriesReader(Protocol):
    async def all(self, user_id: UUID) -> tuple[CategoryView, ...]: ...
