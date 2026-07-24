from uuid import UUID

from src.modules.auth.adapters.outbound.persistence.documents.email_verification_code_document import (  # noqa: E501
    EmailVerificationCodeDocument,
)
from src.modules.auth.adapters.outbound.persistence.mappers.email_verification_code_mapper import (
    EmailVerificationCodeMapper,
)
from src.modules.auth.domain.entities.email_verification_code import EmailVerificationCode


class MongoVerificationCodeRepository:
    """Beanie/Mongo implementation of `VerificationCodeRepository`.

    One active code per user (enforced by a unique index on `user_id`); saving
    replaces the current one.
    """

    async def find_active_by_user(self, user_id: UUID) -> EmailVerificationCode | None:
        doc = await EmailVerificationCodeDocument.find_one(
            EmailVerificationCodeDocument.user_id == user_id
        )
        return EmailVerificationCodeMapper.to_domain(doc) if doc else None

    async def save(self, code: EmailVerificationCode) -> None:
        existing = await EmailVerificationCodeDocument.find_one(
            EmailVerificationCodeDocument.user_id == code.user_id
        )
        if existing is None:
            await EmailVerificationCodeMapper.to_document(code).insert()
            return

        existing.code = code.code
        existing.expires_at = code.expires_at
        existing.attempts = code.attempts
        existing.resend_available_at = code.resend_available_at
        existing.created_at = code.created_at
        await existing.save()

    async def delete_by_user(self, user_id: UUID) -> None:
        existing = await EmailVerificationCodeDocument.find_one(
            EmailVerificationCodeDocument.user_id == user_id
        )
        if existing is not None:
            await existing.delete()
