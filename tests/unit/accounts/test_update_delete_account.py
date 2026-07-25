from dataclasses import replace

import pytest

from src.modules.accounts.application.dto.account_commands import (
    DeleteAccountInputDTO,
    UpdateAccountInputDTO,
)
from src.modules.accounts.application.use_cases.delete_account import DeleteAccountUseCase
from src.modules.accounts.application.use_cases.update_account import UpdateAccountUseCase
from src.modules.accounts.domain.errors import (
    AccountNotFoundError,
    InvalidAccountError,
)

from .fakes import InMemoryAccountRepository, make_account, new_user_id


@pytest.mark.asyncio
async def test_editing_the_balance_shifts_the_anchor_by_the_same_delta() -> None:
    user_id = new_user_id()
    account = make_account(user_id, balance=450_000)
    repository = InMemoryAccountRepository(account)
    use_case = UpdateAccountUseCase(account_repository=repository)

    output = await use_case.execute(
        UpdateAccountInputDTO(user_id=user_id, account_id=account.id, balance=500_000)
    )

    assert output.balance == 500_000
    stored = repository.accounts[0]
    # initial + Σ movements == balance must keep holding: with no movements yet,
    # the anchor absorbs the whole manual adjustment.
    assert stored.initial_balance == 500_000
    assert stored.balance - stored.initial_balance == 0


@pytest.mark.asyncio
async def test_the_anchor_keeps_recorded_movements_intact() -> None:
    user_id = new_user_id()
    # An account anchored at 400k with -50k of movements applied on top: that is
    # exactly the state the movements module will leave behind.
    moved = replace(make_account(user_id, balance=400_000), balance=350_000)
    repository = InMemoryAccountRepository(moved)
    use_case = UpdateAccountUseCase(account_repository=repository)

    await use_case.execute(
        UpdateAccountInputDTO(user_id=user_id, account_id=moved.id, balance=360_000)
    )

    stored = repository.accounts[0]
    # Movements summed -50k; after correcting the balance up by 10k the anchor
    # moves 10k too, so the movement history still reconciles.
    assert stored.balance == 360_000
    assert stored.initial_balance == 410_000


@pytest.mark.asyncio
async def test_updates_only_the_provided_fields() -> None:
    user_id = new_user_id()
    account = make_account(user_id, name="Nequi", balance=450_000)
    repository = InMemoryAccountRepository(account)
    use_case = UpdateAccountUseCase(account_repository=repository)

    output = await use_case.execute(
        UpdateAccountInputDTO(user_id=user_id, account_id=account.id, sub="Ahorros")
    )

    assert output.sub == "Ahorros"
    assert output.name == "Nequi"
    assert output.balance == 450_000


@pytest.mark.asyncio
async def test_rejects_a_blank_name_on_update() -> None:
    user_id = new_user_id()
    account = make_account(user_id)
    use_case = UpdateAccountUseCase(account_repository=InMemoryAccountRepository(account))

    with pytest.raises(InvalidAccountError):
        await use_case.execute(
            UpdateAccountInputDTO(user_id=user_id, account_id=account.id, name=" ")
        )


@pytest.mark.asyncio
async def test_cannot_update_another_users_account() -> None:
    owner_id = new_user_id()
    account = make_account(owner_id)
    use_case = UpdateAccountUseCase(account_repository=InMemoryAccountRepository(account))

    with pytest.raises(AccountNotFoundError):
        await use_case.execute(
            UpdateAccountInputDTO(user_id=new_user_id(), account_id=account.id, name="Robada")
        )


@pytest.mark.asyncio
async def test_deletes_the_account() -> None:
    user_id = new_user_id()
    account = make_account(user_id)
    repository = InMemoryAccountRepository(account)
    use_case = DeleteAccountUseCase(account_repository=repository)

    await use_case.execute(DeleteAccountInputDTO(user_id=user_id, account_id=account.id))

    assert repository.accounts == []


@pytest.mark.asyncio
async def test_cannot_delete_another_users_account() -> None:
    owner_id = new_user_id()
    account = make_account(owner_id)
    repository = InMemoryAccountRepository(account)
    use_case = DeleteAccountUseCase(account_repository=repository)

    with pytest.raises(AccountNotFoundError):
        await use_case.execute(DeleteAccountInputDTO(user_id=new_user_id(), account_id=account.id))
    assert len(repository.accounts) == 1
