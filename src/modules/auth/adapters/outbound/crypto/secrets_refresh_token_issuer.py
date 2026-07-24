import hashlib
import secrets


class SecretsRefreshTokenIssuer:
    """`RefreshTokenIssuer` backed by `secrets` for entropy and SHA-256 for storage.

    Refresh tokens are high-entropy opaque strings, so a fast digest is the
    standard fingerprint; the raw value is never persisted.
    """

    def issue(self) -> tuple[str, str]:
        raw_token = secrets.token_urlsafe(32)
        return raw_token, self.hash(raw_token)

    def hash(self, raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
