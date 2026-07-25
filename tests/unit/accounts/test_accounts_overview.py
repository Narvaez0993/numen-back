import pytest

from src.modules.accounts.application.dto.accounts_overview import (
    AccountsOverviewInputDTO,
)
from src.modules.accounts.application.use_cases.get_accounts_overview import (
    GetAccountsOverviewUseCase,
)

from .fakes import (
    InMemoryAccountRepository,
    InMemoryCreditCardRepository,
    make_account,
    make_card,
    new_user_id,
)


def build(
    accounts: InMemoryAccountRepository, cards: InMemoryCreditCardRepository
) -> GetAccountsOverviewUseCase:
    return GetAccountsOverviewUseCase(account_repository=accounts, credit_card_repository=cards)


@pytest.mark.asyncio
async def test_totals_split_debit_from_cash_and_subtract_card_debt() -> None:
    user_id = new_user_id()
    accounts = InMemoryAccountRepository(
        make_account(user_id, name="BBVA", balance=2_845_000),
        make_account(user_id, name="Bancolombia", balance=2_245_000),
        make_account(user_id, kind="cash", name="Efectivo", balance=155_000),
    )
    cards = InMemoryCreditCardRepository(make_card(user_id, debt=850_000))

    output = await build(accounts, cards).execute(
        AccountsOverviewInputDTO(user_id=user_id, currency="COP")
    )

    assert output.debit_total == 5_090_000
    assert output.cash_total == 155_000
    assert output.tc_debt == 850_000
    assert output.net_balance == 4_395_000
    assert (output.accounts_count, output.credit_cards_count) == (3, 1)
    assert output.currency == "COP"


@pytest.mark.asyncio
async def test_empty_overview_is_all_zeros() -> None:
    output = await build(InMemoryAccountRepository(), InMemoryCreditCardRepository()).execute(
        AccountsOverviewInputDTO(user_id=new_user_id(), currency="USD")
    )

    assert output.accounts == []
    assert output.credit_cards == []
    assert output.net_balance == 0
    assert output.currency == "USD"


@pytest.mark.asyncio
async def test_never_leaks_another_tenants_sources() -> None:
    user_id = new_user_id()
    other_id = new_user_id()
    accounts = InMemoryAccountRepository(
        make_account(user_id, name="Mía", balance=100_000),
        make_account(other_id, name="Ajena", balance=999_000),
    )
    cards = InMemoryCreditCardRepository(make_card(other_id, debt=500_000))

    output = await build(accounts, cards).execute(
        AccountsOverviewInputDTO(user_id=user_id, currency="COP")
    )

    assert [a.name for a in output.accounts] == ["Mía"]
    assert output.net_balance == 100_000


@pytest.mark.asyncio
async def test_an_overdrawn_account_lowers_the_net_balance() -> None:
    user_id = new_user_id()
    accounts = InMemoryAccountRepository(
        make_account(user_id, name="Banco", balance=200_000),
        make_account(user_id, name="Sobregirada", balance=-50_000),
    )

    output = await build(accounts, InMemoryCreditCardRepository()).execute(
        AccountsOverviewInputDTO(user_id=user_id, currency="COP")
    )

    assert output.debit_total == 150_000
    assert output.net_balance == 150_000
