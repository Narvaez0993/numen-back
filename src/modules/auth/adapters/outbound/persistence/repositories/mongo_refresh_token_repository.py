from datetime import datetime
from uuid import UUID

from src.modules.auth.adapters.outbound.persistence.documents.refresh_token_document import (
    RefreshTokenDocument,
)
from src.modules.auth.adapters.outbound.persistence.mappers.refresh_token_mapper import (
    RefreshTokenMapper,
)
from src.modules.auth.domain.entities.refresh_token import RefreshToken


class MongoRefreshTokenRepository:
    """Beanie/Mongo implementation of `RefreshTokenRepository`."""

    async def save(self, token: RefreshToken) -> None:
        existing = await RefreshTokenDocument.get(str(token.id))
        if existing is None:
            await RefreshTokenMapper.to_document(token).insert()
            return

        existing.revoked_at = token.revoked_at
        await existing.save()

    async def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        doc = await RefreshTokenDocument.find_one(
            RefreshTokenDocument.token_hash == token_hash
        )
        return RefreshTokenMapper.to_domain(doc) if doc else None

    async def revoke_family(self, family_id: UUID, revoked_at: datetime) -> None:
        docs = await RefreshTokenDocument.find(
            RefreshTokenDocument.family_id == str(family_id)
        ).to_list()
        for doc in docs:
            if doc.revoked_at is None:
                doc.revoked_at = revoked_at
                await doc.save()
