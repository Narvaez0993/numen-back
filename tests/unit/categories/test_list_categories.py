from uuid import uuid4

import pytest

from src.modules.categories.application.dto.list_categories import ListCategoriesInputDTO
from src.modules.categories.application.use_cases.list_categories import (
    ListCategoriesUseCase,
)
from src.modules.categories.domain.entities.category import Category
from src.modules.categories.domain.standard_catalog import STANDARD_CATEGORIES
from tests.unit.categories.fakes import InMemoryCategoryRepository


@pytest.mark.asyncio
async def test_lists_standard_plus_own_custom() -> None:
    uid = uuid4()
    custom = Category.create_custom(
        user_id=uid, name="Mascotas", icon="dots", color="pink", flow="expense"
    )
    repo = InMemoryCategoryRepository(custom)
    out = await ListCategoriesUseCase(category_repository=repo).execute(
        ListCategoriesInputDTO(user_id=uid)
    )

    standard = [c for c in out.categories if c.is_standard]
    assert len(standard) == len(STANDARD_CATEGORIES)
    ids = {c.id for c in out.categories}
    assert "mercado" in ids  # standard expense
    assert "salario" in ids  # standard income
    assert any(c.name == "Mascotas" and not c.is_standard for c in out.categories)


@pytest.mark.asyncio
async def test_excludes_other_users_custom() -> None:
    mine = uuid4()
    other = uuid4()
    repo = InMemoryCategoryRepository(
        Category.create_custom(
            user_id=other, name="Ajeno", icon="dots", color="mint", flow="expense"
        )
    )
    out = await ListCategoriesUseCase(category_repository=repo).execute(
        ListCategoriesInputDTO(user_id=mine)
    )
    assert all(c.is_standard for c in out.categories)
