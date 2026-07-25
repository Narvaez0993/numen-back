from uuid import UUID, uuid4

import pytest

from src.modules.categories.application.dto.create_category import CreateCategoryInputDTO
from src.modules.categories.application.use_cases.create_category import (
    CreateCategoryUseCase,
)
from src.modules.categories.domain.errors import (
    CategoryLimitReachedError,
    CategoryNameTakenError,
    InvalidCategoryError,
)
from tests.unit.categories.fakes import InMemoryCategoryRepository


def _use_case(repo: InMemoryCategoryRepository, free_limit: int = 2) -> CreateCategoryUseCase:
    return CreateCategoryUseCase(category_repository=repo, free_limit=free_limit)


def _input(
    user_id: UUID,
    name: str,
    *,
    tier: str = "free",
    color: str = "mint",
    flow: str = "expense",
    icon: str = "dots",
) -> CreateCategoryInputDTO:
    return CreateCategoryInputDTO(
        user_id=user_id, tier=tier, name=name, icon=icon, color=color, flow=flow
    )


@pytest.mark.asyncio
async def test_creates_custom_category() -> None:
    repo = InMemoryCategoryRepository()
    uid = uuid4()
    out = await _use_case(repo).execute(_input(uid, "Mascotas", color="pink"))
    assert out.name == "Mascotas"
    assert out.is_standard is False
    assert len(await repo.list_by_user(uid)) == 1


@pytest.mark.asyncio
async def test_free_limit_blocks_beyond_two() -> None:
    repo = InMemoryCategoryRepository()
    uid = uuid4()
    use_case = _use_case(repo, free_limit=2)
    await use_case.execute(_input(uid, "Uno"))
    await use_case.execute(_input(uid, "Dos"))
    with pytest.raises(CategoryLimitReachedError):
        await use_case.execute(_input(uid, "Tres"))


@pytest.mark.asyncio
async def test_plus_bypasses_free_limit() -> None:
    repo = InMemoryCategoryRepository()
    uid = uuid4()
    use_case = _use_case(repo, free_limit=2)
    for name in ("Uno", "Dos", "Tres"):
        await use_case.execute(_input(uid, name, tier="plus"))
    assert len(await repo.list_by_user(uid)) == 3


@pytest.mark.asyncio
async def test_rejects_standard_name() -> None:
    repo = InMemoryCategoryRepository()
    with pytest.raises(CategoryNameTakenError):
        await _use_case(repo).execute(_input(uuid4(), "Café", color="amber"))


@pytest.mark.asyncio
async def test_rejects_duplicate_custom_name_case_insensitive() -> None:
    repo = InMemoryCategoryRepository()
    uid = uuid4()
    use_case = _use_case(repo)
    await use_case.execute(_input(uid, "Mascotas", color="pink"))
    with pytest.raises(CategoryNameTakenError):
        await use_case.execute(_input(uid, "  mascotas ", color="pink"))


@pytest.mark.asyncio
async def test_rejects_invalid_color() -> None:
    repo = InMemoryCategoryRepository()
    with pytest.raises(InvalidCategoryError):
        await _use_case(repo).execute(_input(uuid4(), "X", color="gold"))


@pytest.mark.asyncio
async def test_rejects_invalid_flow() -> None:
    repo = InMemoryCategoryRepository()
    with pytest.raises(InvalidCategoryError):
        await _use_case(repo).execute(_input(uuid4(), "Y", flow="savings"))


@pytest.mark.asyncio
async def test_rejects_blank_name() -> None:
    repo = InMemoryCategoryRepository()
    with pytest.raises(InvalidCategoryError):
        await _use_case(repo).execute(_input(uuid4(), "   "))
