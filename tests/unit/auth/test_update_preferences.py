import pytest

from src.modules.auth.application.dto.update_preferences import UpdatePreferencesInputDTO
from src.modules.auth.application.use_cases.update_preferences import (
    UpdatePreferencesUseCase,
)
from src.modules.auth.domain.value_objects.preferences import InvalidPreferencesError

from .fakes import InMemoryAuthRepository, make_user


@pytest.mark.asyncio
async def test_updates_currency_and_leaves_the_rest_untouched() -> None:
    user = make_user(verified=True)
    repository = InMemoryAuthRepository(user)
    use_case = UpdatePreferencesUseCase(auth_repository=repository)

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
    use_case = UpdatePreferencesUseCase(auth_repository=InMemoryAuthRepository(user))

    output = await use_case.execute(UpdatePreferencesInputDTO(user_id=user.id, currency=" cop "))

    assert output.currency == "COP"


@pytest.mark.asyncio
async def test_rejects_an_unsupported_currency() -> None:
    user = make_user(verified=True)
    use_case = UpdatePreferencesUseCase(auth_repository=InMemoryAuthRepository(user))

    with pytest.raises(InvalidPreferencesError):
        await use_case.execute(UpdatePreferencesInputDTO(user_id=user.id, currency="BTC"))


@pytest.mark.asyncio
async def test_rejects_an_unsupported_language() -> None:
    user = make_user(verified=True)
    use_case = UpdatePreferencesUseCase(auth_repository=InMemoryAuthRepository(user))

    with pytest.raises(InvalidPreferencesError):
        await use_case.execute(UpdatePreferencesInputDTO(user_id=user.id, language="fr"))


@pytest.mark.asyncio
async def test_updates_language_and_theme_together() -> None:
    user = make_user(verified=True)
    use_case = UpdatePreferencesUseCase(auth_repository=InMemoryAuthRepository(user))

    output = await use_case.execute(
        UpdatePreferencesInputDTO(user_id=user.id, language="en", theme="dark")
    )

    assert (output.language, output.theme, output.currency) == ("en", "dark", "USD")
