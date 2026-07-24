from src.modules.auth.adapters.outbound.persistence.documents.email_verification_code_document import (  # noqa: E501
    EmailVerificationCodeDocument,
)
from src.modules.auth.domain.entities.email_verification_code import EmailVerificationCode


class EmailVerificationCodeMapper:
    @staticmethod
    def to_domain(doc: EmailVerificationCodeDocument) -> EmailVerificationCode:
        return EmailVerificationCode(
            user_id=doc.user_id,
            code=doc.code,
            expires_at=doc.expires_at,
            attempts=doc.attempts,
            resend_available_at=doc.resend_available_at,
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(code: EmailVerificationCode) -> EmailVerificationCodeDocument:
        return EmailVerificationCodeDocument(
            user_id=code.user_id,
            code=code.code,
            expires_at=code.expires_at,
            attempts=code.attempts,
            resend_available_at=code.resend_available_at,
            created_at=code.created_at,
        )
