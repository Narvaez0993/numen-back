import pytest

from src.modules.auth.application.dto.update_preferences import UpdatePreferencesInputDTO
from src.modules.auth.application.use_cases.update_preferences import (
    UpdatePreferencesUseCase,
)
from src.modules.auth.domain.errors import CurrencyChangeBlockedError
from src.modules.auth.domain.value_objects.preferences import InvalidPreferencesError

from .fakes import (
    FakeCurrencyScope,
    ImmediateUnitOfWork,
    InMemoryAuthRepository,
    make_user,
)


def build(repository: InMemoryAuthRepository, scope: FakeCurrencyScope | None = None):
    return UpdatePreferencesUseCase(
        auth_repository=repository,
        currency_scope=scope or FakeCurrencyScope(),
        unit_of_work=ImmediateUnitOfWork(),
    )


@pytest.mark.asyncio
async def test_updates_currency_and_leaves_the_rest_untouched() -> None:
    user = make_user(verified=True)
    repository = InMemoryAuthRepository(user)
    use_case = build(repository)

    output = await use_case.execute(UpdatePreferencesInputDTO(user_id=user.id, currency="COP"))

    assert output.currency == "COP"
    assert output.language == "es"
    assert output.theme == "system"
    stored = await repository.find_by_id(user.id)
    assert stored is not None
    assert stored.preferences.currency == "COP"


@pytest.mark.asyncio
async def test_normalizes_the_currency_code() -> None:
    user = make_user(verified=True)
    use_case = build(InMemoryAuthRepository(user))

    output = await use_case.execute(UpdatePreferencesInputDTO(user_id=user.id, currency=" cop "))

    assert output.currency == "COP"


@pytest.mark.asyncio
async def test_rejects_an_unsupported_currency() -> None:
    user = make_user(verified=True)
    use_case = build(InMemoryAuthRepository(user))

    with pytest.raises(InvalidPreferencesError):
        await use_case.execute(UpdatePreferencesInputDTO(user_id=user.id, currency="BTC"))


@pytest.mark.asyncio
async def test_rejects_an_unsupported_language() -> None:
    user = make_user(verified=True)
    use_case = build(InMemoryAuthRepository(user))

    with pytest.raises(InvalidPreferencesError):
        await use_case.execute(UpdatePreferencesInputDTO(user_id=user.id, language="fr"))


@pytest.mark.asyncio
async def test_updates_language_and_theme_together() -> None:
    user = make_user(verified=True)
    use_case = build(InMemoryAuthRepository(user))

    output = await use_case.execute(
        UpdatePreferencesInputDTO(user_id=user.id, language="en", theme="dark")
    )

    assert (output.language, output.theme, output.currency) == ("en", "dark", "USD")


@pytest.mark.asyncio
async def test_changing_the_currency_restamps_the_users_sources() -> None:
    """Otherwise the accounts keep the old currency and every movement on them is
    rejected for a mismatch the user cannot see."""
    user = make_user(verified=True)
    scope = FakeCurrencyScope(history=False)
    use_case = build(InMemoryAuthRepository(user), scope)

    await use_case.execute(UpdatePreferencesInputDTO(user_id=user.id, currency="COP"))

    assert scope.restamped == ["COP"]


@pytest.mark.asyncio
async def test_the_currency_cannot_change_once_there_is_history() -> None:
    """Amounts are stored in the minor unit and the exponent differs (COP 0, USD 2),
    so re-labelling a history would move every decimal point."""
    user = make_user(verified=True)
    repository = InMemoryAuthRepository(user)
    scope = FakeCurrencyScope(history=True)

    with pytest.raises(CurrencyChangeBlockedError):
        await build(repository, scope).execute(
            UpdatePreferencesInputDTO(user_id=user.id, currency="COP")
        )

    stored = await repository.find_by_id(user.id)
    assert stored is not None
    assert stored.preferences.currency == "USD"  # untouched
    assert scope.restamped == []


@pytest.mark.asyncio
async def test_history_does_not_block_language_or_theme() -> None:
    """Only the currency is dangerous; the rest stay free to change."""
    user = make_user(verified=True)
    scope = FakeCurrencyScope(history=True)

    output = await build(InMemoryAuthRepository(user), scope).execute(
        UpdatePreferencesInputDTO(user_id=user.id, language="en", theme="dark")
    )

    assert (output.language, output.theme) == ("en", "dark")
    assert scope.restamped == []


@pytest.mark.asyncio
async def test_setting_the_same_currency_again_restamps_nothing() -> None:
    user = make_user(verified=True)
    scope = FakeCurrencyScope(history=True)

    output = await build(InMemoryAuthRepository(user), scope).execute(
        UpdatePreferencesInputDTO(user_id=user.id, currency="USD")
    )

    assert output.currency == "USD"
    assert scope.restamped == []


@pytest.mark.asyncio
async def test_the_objective_is_stored_and_travels_in_the_profile() -> None:
    """What the user came for decides which figure Home leads with, so it lives with
    the user and not on the device — a preference that vanishes on reinstall cannot
    anchor anything."""
    user = make_user(verified=True)
    repository = InMemoryAuthRepository(user)

    output = await build(repository).execute(
        UpdatePreferencesInputDTO(user_id=user.id, objective="deudas")
    )

    assert output.objective == "deudas"
    stored = await repository.find_by_id(user.id)
    assert stored is not None
    assert stored.preferences.objective == "deudas"


@pytest.mark.asyncio
async def test_an_unknown_objective_is_refused() -> None:
    user = make_user(verified=True)

    with pytest.raises(InvalidPreferencesError):
        await build(InMemoryAuthRepository(user)).execute(
            UpdatePreferencesInputDTO(user_id=user.id, objective="hacerme-rico")
        )


@pytest.mark.asyncio
async def test_an_absent_objective_keeps_the_stored_one() -> None:
    user = make_user(verified=True)
    repository = InMemoryAuthRepository(user)
    await build(repository).execute(UpdatePreferencesInputDTO(user_id=user.id, objective="ahorrar"))

    output = await build(repository).execute(
        UpdatePreferencesInputDTO(user_id=user.id, theme="dark")
    )

    assert (output.objective, output.theme) == ("ahorrar", "dark")


@pytest.mark.asyncio
async def test_a_user_starts_without_an_objective() -> None:
    """Skipping the question is allowed; Home falls back to the spending pace."""
    user = make_user(verified=True)

    output = await build(InMemoryAuthRepository(user)).execute(
        UpdatePreferencesInputDTO(user_id=user.id, theme="dark")
    )

    assert output.objective is None
