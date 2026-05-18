from typing import cast

from src.modules.auth.adapters.outbound.persistence.documents.user_document import UserDocument
from src.modules.auth.domain.entities.user import Tier, User
from src.modules.auth.domain.value_objects.email import Email
from src.modules.auth.domain.value_objects.hashed_password import HashedPassword


class UserMapper:
    @staticmethod
    def to_domain(doc: UserDocument) -> User:
        return User(
            id=doc.id,
            email=Email(value=doc.email),
            display_name=doc.display_name,
            hashed_password=HashedPassword(value=doc.hashed_password),
            tier=cast(Tier, doc.tier),
            created_at=doc.created_at,
        )

    @staticmethod
    def to_document(user: User) -> UserDocument:
        return UserDocument(
            id=user.id,
            email=user.email.value,
            display_name=user.display_name,
            hashed_password=user.hashed_password.value,
            tier=user.tier,
            created_at=user.created_at,
        )
