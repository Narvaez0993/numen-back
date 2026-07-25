from pydantic import BaseModel


class AuthSessionDTO(BaseModel):
    """Authenticated session returned by verify-email, login and refresh."""

    user_id: str
    email: str
    display_name: str
    tier: str
    # Carried in the session payload so the client can format money right away
    # without a second call to /auth/me.
    language: str
    currency: str
    theme: str
    access_token: str
    refresh_token: str
