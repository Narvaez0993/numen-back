from src.modules.auth.adapters.outbound.persistence.documents.refresh_token_document import (
    RefreshTokenDocument,
)
from src.modules.auth.domain.entities.refresh_token import RefreshToken


class RefreshTokenMapper:
    @staticmethod
    def to_domain(doc: RefreshTokenDocument) -> RefreshToken:
        return RefreshToken(
            id=doc.id,
            user_id=doc.user_id,
            token_hash=doc.token_hash,
            family_id=doc.family_id,
            expires_at=doc.expires_at,
            created_at=doc.created_at,
            revoked_at=doc.revoked_at,
        )

    @staticmethod
    def to_document(token: RefreshToken) -> RefreshTokenDocument:
        return RefreshTokenDocument(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            family_id=token.family_id,
            expires_at=token.expires_at,
            created_at=token.created_at,
            revoked_at=token.revoked_at,
        )
