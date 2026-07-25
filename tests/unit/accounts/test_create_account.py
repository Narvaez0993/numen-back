import pytest

from src.modules.accounts.application.dto.account_commands import CreateAccountInputDTO
from src.modules.accounts.application.use_cases.create_account import CreateAccountUseCase
from src.modules.accounts.domain.errors import (
    AccountLimitReachedError,
    InvalidAccountError,
)

from .fakes import FixedClock, InMemoryAccountRepository, make_account, new_user_id


def build(repository: InMemoryAccountRepository, free_limit: int = 2) -> CreateAccountUseCase:
    return CreateAccountUseCase(
        account_repository=repository,
        clock=FixedClock(),
        free_limit=free_limit,
    )


def payload(user_id, **overrides):  # type: ignore[no-untyped-def]
    base = {
        "user_id": user_id,
        "tier": "free",
        "currency": "COP",
        "kind": "debit",
        "name": "Nequi",
        "balance": 450_000,
    }
    base.update(overrides)
    return CreateAccountInputDTO(**base)


@pytest.mark.asyncio
async def test_creates_an_account_anchored_to_its_initial_balance() -> None:
    user_id = new_user_id()
    repository = InMemoryAccountRepository()

    output = await build(repository).execute(payload(user_id))

    assert output.name == "Nequi"
    assert output.balance == 450_000
    assert output.currency == "COP"
    stored = repository.accounts[0]
    assert stored.initial_balance == 450_000


@pytest.mark.asyncio
async def test_defaults_the_icon_per_kind_and_the_color() -> None:
    user_id = new_user_id()
    repository = InMemoryAccountRepository()

    debit = await build(repository).execute(payload(user_id, name="Banco"))
    cash = await build(repository).execute(
        payload(user_id, kind="cash", name="Efectivo", tier="plus")
    )

    assert debit.icon == "building-bank"
    assert debit.color == "mint"
    assert cash.icon == "cash"


@pytest.mark.asyncio
async def test_rejects_a_third_account_on_free() -> None:
    user_id = new_user_id()
    repository = InMemoryAccountRepository(
        make_account(user_id, name="A"), make_account(user_id, name="B")
    )

    with pytest.raises(AccountLimitReachedError):
        await build(repository).execute(payload(user_id))


@pytest.mark.asyncio
async def test_allows_more_accounts_on_plus() -> None:
    user_id = new_user_id()
    repository = InMemoryAccountRepository(
        make_account(user_id, name="A"), make_account(user_id, name="B")
    )

    output = await build(repository).execute(payload(user_id, tier="plus", name="C"))

    assert output.name == "C"
    assert len(repository.accounts) == 3


@pytest.mark.asyncio
async def test_counts_only_the_callers_accounts_for_the_gate() -> None:
    user_id = new_user_id()
    other_id = new_user_id()
    repository = InMemoryAccountRepository(
        make_account(other_id, name="A"), make_account(other_id, name="B")
    )

    output = await build(repository).execute(payload(user_id))

    assert output.name == "Nequi"


@pytest.mark.asyncio
async def test_rejects_an_unknown_kind() -> None:
    with pytest.raises(InvalidAccountError):
        await build(InMemoryAccountRepository()).execute(payload(new_user_id(), kind="crypto"))


@pytest.mark.asyncio
async def test_rejects_a_blank_name() -> None:
    with pytest.raises(InvalidAccountError):
        await build(InMemoryAccountRepository()).execute(payload(new_user_id(), name="   "))


@pytest.mark.asyncio
async def test_rejects_an_unknown_color() -> None:
    with pytest.raises(InvalidAccountError):
        await build(InMemoryAccountRepository()).execute(payload(new_user_id(), color="chartreuse"))


@pytest.mark.asyncio
async def test_accepts_a_negative_balance_for_an_overdrawn_account() -> None:
    user_id = new_user_id()
    repository = InMemoryAccountRepository()

    output = await build(repository).execute(payload(user_id, balance=-120_000))

    assert output.balance == -120_000
