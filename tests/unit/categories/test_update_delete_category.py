from uuid import UUID, uuid4

import pytest

from src.modules.categories.application.dto.delete_category import DeleteCategoryInputDTO
from src.modules.categories.application.dto.update_category import UpdateCategoryInputDTO
from src.modules.categories.application.use_cases.delete_category import (
    DeleteCategoryUseCase,
)
from src.modules.categories.application.use_cases.update_category import (
    UpdateCategoryUseCase,
)
from src.modules.categories.domain.entities.category import Category
from src.modules.categories.domain.errors import (
    CategoryNameTakenError,
    CategoryNotFoundError,
)
from tests.unit.categories.fakes import InMemoryCategoryRepository


def _custom(user_id: UUID, name: str, color: str = "mint") -> Category:
    return Category.create_custom(
        user_id=user_id, name=name, icon="dots", color=color, flow="expense"
    )


@pytest.mark.asyncio
async def test_updates_name_and_color() -> None:
    uid = uuid4()
    cat = _custom(uid, "Mascotas")
    repo = InMemoryCategoryRepository(cat)
    out = await UpdateCategoryUseCase(category_repository=repo).execute(
        UpdateCategoryInputDTO(user_id=uid, category_id=cat.id, name="Perros", color="coral")
    )
    assert out.name == "Perros"
    assert out.color == "coral"


@pytest.mark.asyncio
async def test_update_unknown_raises_not_found() -> None:
    uid = uuid4()
    repo = InMemoryCategoryRepository()
    with pytest.raises(CategoryNotFoundError):
        await UpdateCategoryUseCase(category_repository=repo).execute(
            UpdateCategoryInputDTO(user_id=uid, category_id="cafe", name="X")
        )


@pytest.mark.asyncio
async def test_update_rejects_duplicate_name() -> None:
    uid = uuid4()
    a = _custom(uid, "Mascotas")
    b = _custom(uid, "Gimnasio")
    repo = InMemoryCategoryRepository(a, b)
    with pytest.raises(CategoryNameTakenError):
        await UpdateCategoryUseCase(category_repository=repo).execute(
            UpdateCategoryInputDTO(user_id=uid, category_id=b.id, name="mascotas")
        )


@pytest.mark.asyncio
async def test_deletes_custom() -> None:
    uid = uuid4()
    cat = _custom(uid, "Mascotas")
    repo = InMemoryCategoryRepository(cat)
    await DeleteCategoryUseCase(category_repository=repo).execute(
        DeleteCategoryInputDTO(user_id=uid, category_id=cat.id)
    )
    assert await repo.list_by_user(uid) == []


@pytest.mark.asyncio
async def test_delete_unknown_raises_not_found() -> None:
    uid = uuid4()
    repo = InMemoryCategoryRepository()
    with pytest.raises(CategoryNotFoundError):
        await DeleteCategoryUseCase(category_repository=repo).execute(
            DeleteCategoryInputDTO(user_id=uid, category_id="nope")
        )
