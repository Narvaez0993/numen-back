from typing import cast
from uuid import UUID

from src.modules.auth.adapters.outbound.persistence.documents.user_document import (
    UserDocument,
    UserPreferencesDocument,
)
from src.modules.auth.domain.entities.user import Tier, User
from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.domain.value_objects.hashed_password import HashedPassword
from src.modules.auth.domain.value_objects.preferences import (
    Language,
    Objective,
    Theme,
    UserPreferences,
)


class UserMapper:
    @staticmethod
    def to_domain(doc: UserDocument) -> User:
        return User(
            id=UUID(doc.id),
            email=Email(value=doc.email),
            display_name=doc.display_name,
            hashed_password=HashedPassword(value=doc.hashed_password),
            tier=cast(Tier, doc.tier),
            email_verified=doc.email_verified,
            created_at=doc.created_at,
            preferences=UserPreferences(
                language=cast(Language, doc.preferences.language),
                currency=doc.preferences.currency,
                theme=cast(Theme, doc.preferences.theme),
                objective=cast(Objective | None, doc.preferences.objective),
            ),
        )

    @staticmethod
    def to_document(user: User) -> UserDocument:
        return UserDocument(
            id=str(user.id),
            email=user.email.value,
            display_name=user.display_name,
            hashed_password=user.hashed_password.value,
            tier=user.tier,
            email_verified=user.email_verified,
            created_at=user.created_at,
            preferences=UserPreferencesDocument(
                language=user.preferences.language,
                currency=user.preferences.currency,
                theme=user.preferences.theme,
                objective=user.preferences.objective,
            ),
        )
