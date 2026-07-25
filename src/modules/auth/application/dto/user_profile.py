from pydantic import BaseModel

from src.modules.auth.domain.entities.user import User


class UserProfileDTO(BaseModel):
    """The authenticated user, as every profile-shaped endpoint returns it.

    One shape for `GET /auth/me`, `PATCH /auth/me` and
    `PATCH /auth/me/preferences` so the client parses a single payload.
    """

    user_id: str
    email: str
    display_name: str
    tier: str
    email_verified: bool
    language: str
    currency: str
    theme: str

    @classmethod
    def from_domain(cls, user: User) -> "UserProfileDTO":
        return cls(
            user_id=str(user.id),
            email=user.email.value,
            display_name=user.display_name,
            tier=user.tier,
            email_verified=user.email_verified,
            language=user.preferences.language,
            currency=user.preferences.currency,
            theme=user.preferences.theme,
        )
