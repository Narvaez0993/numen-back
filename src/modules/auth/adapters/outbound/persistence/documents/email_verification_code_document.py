from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from beanie import Document, Indexed
from pydantic import Field


class EmailVerificationCodeDocument(Document):
    id: UUID = Field(default_factory=uuid4)  # type: ignore[assignment]
    user_id: Annotated[UUID, Indexed(unique=True)]
    code: str
    expires_at: datetime
    attempts: int = 0
    resend_available_at: datetime
    created_at: datetime

    class Settings:
        name = "email_verification_codes"
