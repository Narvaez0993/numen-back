from pydantic import BaseModel


class AuthSessionDTO(BaseModel):
    """Authenticated session returned by verify-email, login and refresh."""

    user_id: str
    email: str
    display_name: str
    tier: str
    access_token: str
    refresh_token: str
