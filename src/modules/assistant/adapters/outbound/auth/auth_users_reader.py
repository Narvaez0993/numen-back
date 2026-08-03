from uuid import UUID

from src.modules.assistant.application.ports.users_reader import UserView
from src.modules.auth.adapters.outbound.persistence.documents.user_document import UserDocument


class AuthUsersReader:
    """`UsersReader` over the users collection.

    Reads the document directly instead of going through an auth use case: auth
    has no reason to grow a "list everyone" operation for its own sake, and an
    adapter touching a sibling's persistence is exactly what adapters may do.
    """

    async def list_users(self, tier: str | None = None) -> tuple[UserView, ...]:
        criteria = {"tier": tier} if tier is not None else {}
        docs = await UserDocument.find(criteria).sort("+preferences.language").to_list()
        return tuple(
            UserView(
                user_id=UUID(doc.id),
                tier=doc.tier,
                language=doc.preferences.language,
                currency=doc.preferences.currency,
                objective=doc.preferences.objective,
            )
            for doc in docs
        )
