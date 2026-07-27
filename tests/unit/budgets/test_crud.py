"""Setting, changing and removing a cap — and the two rules that bound it.

The plan gates **watched categories**, not the ceiling: every user has exactly one month
ceiling, so a second one is a conflict and never an upsell.
"""

import pytest

from src.modules.budgets.application.dto.budget_commands import (
    CreateBudgetInputDTO,
    DeleteBudgetInputDTO,
    UpdateBudgetInputDTO,
)
from src.modules.budgets.application.use_cases.create_budget import CreateBudgetUseCase
from src.modules.budgets.application.use_cases.delete_budget import DeleteBudgetUseCase
from src.modules.budgets.application.use_cases.update_budget import UpdateBudgetUseCase
from src.modules.budgets.domain.errors import (
    BudgetAlreadyExistsError,
    BudgetCategoryNotFoundError,
    BudgetLimitReachedError,
    BudgetNotFoundError,
    InvalidBudgetError,
)

from .fakes import (
    TODAY,
    FakeBudgetRepository,
    FakeCategoryReader,
    budget,
    new_user_id,
)

FREE_CATEGORY_LIMIT = 2


def creator(
    repository: FakeBudgetRepository,
    categories: FakeCategoryReader | None = None,
) -> CreateBudgetUseCase:
    return CreateBudgetUseCase(
        budget_repository=repository,
        category_reader=categories or FakeCategoryReader(),
        category_free_limit=FREE_CATEGORY_LIMIT,
    )


async def create(
    use_case: CreateBudgetUseCase,
    *,
    user_id,
    scope: str = "global",
    category_id: str | None = None,
    target: int = 3_000_000,
    tier: str = "free",
    today: str = TODAY,
):
    return await use_case.execute(
        CreateBudgetInputDTO(
            user_id=user_id,
            tier=tier,
            today=today,
            scope=scope,
            category_id=category_id,
            target=target,
        )
    )


@pytest.mark.asyncio
async def test_a_cap_is_stamped_with_the_month_it_was_set_in() -> None:
    """It is standing, not monthly: `since` records when the number was chosen, and
    August measures against the same cap without anyone touching it."""
    repository = FakeBudgetRepository()

    output = await create(creator(repository), user_id=new_user_id())

    assert output.scope == "global"
    assert output.target == 3_000_000
    assert output.since == "2026-07"
    assert output.category_id is None


@pytest.mark.asyncio
async def test_there_is_only_one_month_ceiling() -> None:
    user_id = new_user_id()
    repository = FakeBudgetRepository([budget(user_id=user_id)])

    with pytest.raises(BudgetAlreadyExistsError):
        await create(creator(repository), user_id=user_id)


@pytest.mark.asyncio
async def test_the_second_cap_on_the_same_category_is_an_edit_not_a_new_one() -> None:
    user_id = new_user_id()
    repository = FakeBudgetRepository(
        [budget(user_id=user_id, scope="category", category_id="mercado", target=400_000)]
    )

    with pytest.raises(BudgetAlreadyExistsError):
        await create(creator(repository), user_id=user_id, scope="category", category_id="mercado")


@pytest.mark.asyncio
async def test_free_watches_two_categories_and_the_third_is_the_upsell() -> None:
    user_id = new_user_id()
    repository = FakeBudgetRepository(
        [
            budget(user_id=user_id, scope="category", category_id="mercado", target=400_000),
            budget(user_id=user_id, scope="category", category_id="domicilios", target=200_000),
        ]
    )

    with pytest.raises(BudgetLimitReachedError):
        await create(
            creator(repository), user_id=user_id, scope="category", category_id="transporte"
        )


@pytest.mark.asyncio
async def test_the_ceiling_is_not_part_of_that_gate() -> None:
    """Two watched categories on Free and still no global cap: setting it must work."""
    user_id = new_user_id()
    repository = FakeBudgetRepository(
        [
            budget(user_id=user_id, scope="category", category_id="mercado", target=400_000),
            budget(user_id=user_id, scope="category", category_id="domicilios", target=200_000),
        ]
    )

    output = await create(creator(repository), user_id=user_id)

    assert output.scope == "global"


@pytest.mark.asyncio
async def test_plus_watches_as_many_as_it_likes() -> None:
    user_id = new_user_id()
    repository = FakeBudgetRepository(
        [
            budget(user_id=user_id, scope="category", category_id="mercado", target=400_000),
            budget(user_id=user_id, scope="category", category_id="domicilios", target=200_000),
        ]
    )

    output = await create(
        creator(repository),
        user_id=user_id,
        scope="category",
        category_id="transporte",
        target=150_000,
        tier="plus",
    )

    assert output.category_id == "transporte"


@pytest.mark.asyncio
async def test_a_cap_on_a_category_that_does_not_exist_says_so() -> None:
    """Its own code, so the client can point at the field instead of showing a generic
    validation error for a stale catalog."""
    with pytest.raises(BudgetCategoryNotFoundError):
        await create(
            creator(FakeBudgetRepository()),
            user_id=new_user_id(),
            scope="category",
            category_id="cripto",
        )


@pytest.mark.asyncio
async def test_a_category_cap_needs_a_category() -> None:
    with pytest.raises(InvalidBudgetError):
        await create(creator(FakeBudgetRepository()), user_id=new_user_id(), scope="category")


@pytest.mark.asyncio
async def test_a_ceiling_ignores_a_category_it_was_handed() -> None:
    """`global` means the whole month; carrying a category would make the row ambiguous
    for the unique index."""
    output = await create(
        creator(FakeBudgetRepository()),
        user_id=new_user_id(),
        scope="global",
        category_id="mercado",
    )

    assert output.category_id is None


@pytest.mark.asyncio
async def test_a_cap_of_zero_is_not_a_cap() -> None:
    for target in (0, -100):
        with pytest.raises(InvalidBudgetError):
            await create(creator(FakeBudgetRepository()), user_id=new_user_id(), target=target)


@pytest.mark.asyncio
async def test_an_unknown_scope_is_rejected() -> None:
    with pytest.raises(InvalidBudgetError):
        await create(creator(FakeBudgetRepository()), user_id=new_user_id(), scope="weekly")


@pytest.mark.asyncio
async def test_changing_the_number_restamps_the_month() -> None:
    """Raising a cap on the 12th applies to the month in progress — that is the point."""
    user_id = new_user_id()
    existing = budget(user_id=user_id, target=2_000_000, since="2026-06")
    repository = FakeBudgetRepository([existing])

    output = await UpdateBudgetUseCase(budget_repository=repository).execute(
        UpdateBudgetInputDTO(
            user_id=user_id, today="2026-07-12", budget_id=existing.id, target=2_500_000
        )
    )

    assert output.target == 2_500_000
    assert output.since == "2026-07"
    assert output.id == existing.id


@pytest.mark.asyncio
async def test_a_cap_of_someone_else_does_not_exist() -> None:
    existing = budget(user_id=new_user_id())
    repository = FakeBudgetRepository([existing])

    with pytest.raises(BudgetNotFoundError):
        await UpdateBudgetUseCase(budget_repository=repository).execute(
            UpdateBudgetInputDTO(
                user_id=new_user_id(), today=TODAY, budget_id=existing.id, target=1_000_000
            )
        )


@pytest.mark.asyncio
async def test_removing_a_cap_leaves_everything_else_alone() -> None:
    user_id = new_user_id()
    existing = budget(user_id=user_id)
    other = budget(user_id=user_id, scope="category", category_id="mercado", target=400_000)
    repository = FakeBudgetRepository([existing, other])

    await DeleteBudgetUseCase(budget_repository=repository).execute(
        DeleteBudgetInputDTO(user_id=user_id, budget_id=existing.id)
    )

    assert await repository.list_by_user(user_id) == [other]


@pytest.mark.asyncio
async def test_removing_a_cap_that_is_not_there_says_so() -> None:
    with pytest.raises(BudgetNotFoundError):
        await DeleteBudgetUseCase(budget_repository=FakeBudgetRepository()).execute(
            DeleteBudgetInputDTO(user_id=new_user_id(), budget_id="nope")
        )
