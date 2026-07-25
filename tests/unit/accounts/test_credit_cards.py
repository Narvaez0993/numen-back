import pytest

from src.modules.accounts.application.dto.credit_card_commands import (
    CreateCreditCardInputDTO,
    DeleteCreditCardInputDTO,
    UpdateCreditCardInputDTO,
)
from src.modules.accounts.application.use_cases.create_credit_card import (
    CreateCreditCardUseCase,
)
from src.modules.accounts.application.use_cases.delete_credit_card import (
    DeleteCreditCardUseCase,
)
from src.modules.accounts.application.use_cases.update_credit_card import (
    UpdateCreditCardUseCase,
)
from src.modules.accounts.domain.errors import (
    AccountNotFoundError,
    CreditCardLimitReachedError,
    InvalidAccountError,
)

from .fakes import FixedClock, InMemoryCreditCardRepository, make_card, new_user_id


def build(repository: InMemoryCreditCardRepository, free_limit: int = 1) -> CreateCreditCardUseCase:
    return CreateCreditCardUseCase(
        credit_card_repository=repository,
        clock=FixedClock(),
        free_limit=free_limit,
    )


def payload(user_id, **overrides):  # type: ignore[no-untyped-def]
    base = {
        "user_id": user_id,
        "tier": "free",
        "currency": "COP",
        "name": "Visa",
        "debt": 850_000,
        "limit": 5_000_000,
        "cutoff_day": 25,
        "due_day": 5,
    }
    base.update(overrides)
    return CreateCreditCardInputDTO(**base)


@pytest.mark.asyncio
async def test_creates_a_card_with_its_debt_anchor_and_days() -> None:
    user_id = new_user_id()
    repository = InMemoryCreditCardRepository()

    output = await build(repository).execute(payload(user_id))

    assert (output.debt, output.limit) == (850_000, 5_000_000)
    assert (output.cutoff_day, output.due_day) == (25, 5)
    assert output.icon == "credit-card"
    assert repository.cards[0].initial_debt == 850_000


@pytest.mark.asyncio
async def test_due_day_is_optional() -> None:
    output = await build(InMemoryCreditCardRepository()).execute(
        payload(new_user_id(), due_day=None)
    )

    assert output.due_day is None


@pytest.mark.asyncio
async def test_rejects_a_second_card_on_free() -> None:
    user_id = new_user_id()
    repository = InMemoryCreditCardRepository(make_card(user_id))

    with pytest.raises(CreditCardLimitReachedError):
        await build(repository).execute(payload(user_id))


@pytest.mark.asyncio
async def test_allows_more_cards_on_plus() -> None:
    user_id = new_user_id()
    repository = InMemoryCreditCardRepository(make_card(user_id))

    output = await build(repository).execute(payload(user_id, tier="plus", name="Master"))

    assert output.name == "Master"


@pytest.mark.asyncio
async def test_allows_debt_above_the_limit() -> None:
    """Real cards go over the limit; bookkeeping must not refuse to record it."""
    output = await build(InMemoryCreditCardRepository()).execute(
        payload(new_user_id(), debt=6_000_000, limit=5_000_000)
    )

    assert output.debt == 6_000_000


@pytest.mark.asyncio
async def test_rejects_a_non_positive_limit() -> None:
    with pytest.raises(InvalidAccountError):
        await build(InMemoryCreditCardRepository()).execute(payload(new_user_id(), limit=0))


@pytest.mark.asyncio
async def test_rejects_a_negative_debt() -> None:
    with pytest.raises(InvalidAccountError):
        await build(InMemoryCreditCardRepository()).execute(payload(new_user_id(), debt=-1))


@pytest.mark.asyncio
async def test_rejects_a_day_outside_the_month() -> None:
    with pytest.raises(InvalidAccountError):
        await build(InMemoryCreditCardRepository()).execute(payload(new_user_id(), cutoff_day=32))


@pytest.mark.asyncio
async def test_editing_the_debt_shifts_the_anchor() -> None:
    user_id = new_user_id()
    card = make_card(user_id, debt=850_000)
    repository = InMemoryCreditCardRepository(card)
    use_case = UpdateCreditCardUseCase(credit_card_repository=repository)

    output = await use_case.execute(
        UpdateCreditCardInputDTO(user_id=user_id, card_id=card.id, debt=900_000)
    )

    assert output.debt == 900_000
    assert repository.cards[0].initial_debt == 900_000


@pytest.mark.asyncio
async def test_cannot_update_another_users_card() -> None:
    card = make_card(new_user_id())
    use_case = UpdateCreditCardUseCase(credit_card_repository=InMemoryCreditCardRepository(card))

    with pytest.raises(AccountNotFoundError):
        await use_case.execute(
            UpdateCreditCardInputDTO(user_id=new_user_id(), card_id=card.id, name="Robada")
        )


@pytest.mark.asyncio
async def test_deletes_the_card() -> None:
    user_id = new_user_id()
    card = make_card(user_id)
    repository = InMemoryCreditCardRepository(card)
    use_case = DeleteCreditCardUseCase(credit_card_repository=repository)

    await use_case.execute(DeleteCreditCardInputDTO(user_id=user_id, card_id=card.id))

    assert repository.cards == []
