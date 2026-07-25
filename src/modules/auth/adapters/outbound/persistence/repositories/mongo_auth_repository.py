from uuid import UUID

from src.modules.auth.adapters.outbound.persistence.documents.user_document import (
    UserDocument,
    UserPreferencesDocument,
)
from src.modules.auth.adapters.outbound.persistence.mappers.user_mapper import UserMapper
from src.modules.auth.domain.entities.user import User
from src.modules.auth.domain.value_objects.email import Email


class MongoAuthRepository:
    """Beanie/Mongo implementation of `AuthRepository` protocol."""

    async def find_by_id(self, user_id: UUID) -> User | None:
        doc = await UserDocument.get(str(user_id))
        return UserMapper.to_domain(doc) if doc else None

    async def find_by_email(self, email: Email) -> User | None:
        doc = await UserDocument.find_one(UserDocument.email == email.value)
        return UserMapper.to_domain(doc) if doc else None

    async def save(self, user: User) -> None:
        existing = await UserDocument.get(str(user.id))
        if existing is None:
            await UserMapper.to_document(user).insert()
            return

        existing.email = user.email.value
        existing.display_name = user.display_name
        existing.hashed_password = user.hashed_password.value
        existing.tier = user.tier
        existing.email_verified = user.email_verified
        existing.preferences = UserPreferencesDocument(
            language=user.preferences.language,
            currency=user.preferences.currency,
            theme=user.preferences.theme,
        )
        await existing.save()
