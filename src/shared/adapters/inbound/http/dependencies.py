from uuid import UUID

import jwt
from fastapi import Depends, Header

from src.shared.adapters.outbound.config.settings import Settings, get_settings
from src.shared.domain.errors import UnauthorizedError


def get_current_user_id(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> UUID:
    """Decode the Bearer JWT and return the user id (UUID)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token expired") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid token") from exc

    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise UnauthorizedError("Invalid token subject")

    try:
        return UUID(sub)
    except ValueError as exc:
        raise UnauthorizedError("Invalid token subject format") from exc


async def get_current_tier(
    user_id: UUID = Depends(get_current_user_id),
) -> str:
    """Resolve the caller's plan tier for Free-capacity gates.

    Reads through the composition root's auth repository. Local import keeps this
    inbound adapter decoupled from `core` at module-import time (no cycle) — the
    same bridge the routers use.
    """
    from src.core.di.container import get_container

    user = await get_container().auth_repository.find_by_id(user_id)
    if user is None:
        raise UnauthorizedError("Unknown user")
    return user.tier
