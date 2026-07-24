from typing import Protocol


class RefreshTokenIssuer(Protocol):
    """Outbound port: mints opaque refresh tokens and hashes them for storage.

    `issue` returns the raw token (returned to the client, never stored) and its
    hash (persisted). `hash` re-derives the stored hash from a presented token.
    """

    def issue(self) -> tuple[str, str]: ...

    def hash(self, raw_token: str) -> str: ...
