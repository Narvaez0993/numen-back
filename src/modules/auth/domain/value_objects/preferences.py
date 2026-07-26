from dataclasses import dataclass
from typing import ClassVar, Literal, cast, get_args

from src.shared.domain.errors import ValidationError
from src.shared.domain.money import DEFAULT_CURRENCY, is_supported_currency

Language = Literal["es", "en"]
Theme = Literal["light", "dark", "system"]

ALLOWED_LANGUAGES: tuple[str, ...] = get_args(Language)
ALLOWED_THEMES: tuple[str, ...] = get_args(Theme)


class InvalidPreferencesError(ValidationError):
    code: ClassVar[str] = "auth.invalid_preferences"


@dataclass(frozen=True)
class UserPreferences:
    """User-scoped display settings. `currency` is the user's home currency and
    every amount stored for them is in its minor unit."""

    language: Language
    currency: str
    theme: Theme

    @classmethod
    def default(cls, *, language: str = "es", currency: str | None = None) -> "UserPreferences":
        """Starting settings. `currency` comes from the device's region when the
        client knows it: a Colombian who never opens the picker used to be handed USD
        in silence and typed "1.000.000" meaning pesos.

        An unsupported code falls back instead of failing — a wrong currency is worth
        correcting, not worth blocking a registration over.
        """
        chosen = (currency or "").strip().upper()
        return cls(
            language=cast(Language, language) if language in ALLOWED_LANGUAGES else "es",
            currency=chosen if is_supported_currency(chosen) else DEFAULT_CURRENCY,
            theme="system",
        )

    @classmethod
    def create(cls, language: str, currency: str, theme: str) -> "UserPreferences":
        if language not in ALLOWED_LANGUAGES:
            raise InvalidPreferencesError(f"Unsupported language: {language}")
        if theme not in ALLOWED_THEMES:
            raise InvalidPreferencesError(f"Unsupported theme: {theme}")
        normalized_currency = currency.strip().upper()
        if not is_supported_currency(normalized_currency):
            raise InvalidPreferencesError(f"Unsupported currency: {currency}")
        return cls(
            language=cast(Language, language),
            currency=normalized_currency,
            theme=cast(Theme, theme),
        )

    def patched(
        self,
        *,
        language: str | None = None,
        currency: str | None = None,
        theme: str | None = None,
    ) -> "UserPreferences":
        """Partial update: absent fields keep their current value."""
        return UserPreferences.create(
            language=language if language is not None else self.language,
            currency=currency if currency is not None else self.currency,
            theme=theme if theme is not None else self.theme,
        )
