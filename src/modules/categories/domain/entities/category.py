from dataclasses import dataclass, replace
from typing import Literal
from uuid import UUID, uuid4

CategoryFlow = Literal["expense", "income"]

ALLOWED_FLOWS: frozenset[str] = frozenset({"expense", "income"})
ALLOWED_COLORS: frozenset[str] = frozenset({"mint", "coral", "purple", "amber", "pink", "neutral"})
MAX_NAME_LENGTH = 40


@dataclass(frozen=True)
class Category:
    """A spending/income category.

    Two flavors share one shape: `is_standard` categories come from the code
    catalog (global, `user_id is None`, slug id) and are read-only; custom
    categories are persisted per user (`user_id` set, uuid id).
    """

    id: str
    user_id: UUID | None
    name: str
    icon: str
    color: str
    flow: CategoryFlow
    is_standard: bool

    @classmethod
    def create_custom(
        cls,
        *,
        user_id: UUID,
        name: str,
        icon: str,
        color: str,
        flow: CategoryFlow,
    ) -> "Category":
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            icon=icon,
            color=color,
            flow=flow,
            is_standard=False,
        )

    def with_updates(
        self,
        *,
        name: str | None = None,
        icon: str | None = None,
        color: str | None = None,
    ) -> "Category":
        return replace(
            self,
            name=self.name if name is None else name,
            icon=self.icon if icon is None else icon,
            color=self.color if color is None else color,
        )
