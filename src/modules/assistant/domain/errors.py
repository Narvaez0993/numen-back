from typing import ClassVar

from src.shared.domain.errors import ConflictError, DomainError, ForbiddenError, NotFoundError


class ChatLimitReachedError(ForbiddenError):
    code: ClassVar[str] = "assistant.chat_limit_reached"

    def __init__(self) -> None:
        # Raised past the grace messages too: the nudge lives between limit and
        # limit+grace and is the client's job, driven by the usage payload.
        super().__init__("Monthly chat message limit reached for your plan")


class RegistrationLimitReachedError(ForbiddenError):
    code: ClassVar[str] = "assistant.registration_limit_reached"

    def __init__(self) -> None:
        # Capture never hard-blocks the habit (docs 02): the client answers this
        # by opening the manual form, which is always there.
        super().__init__("Monthly AI-capture limit reached for your plan")


class DraftNotFoundError(NotFoundError):
    code: ClassVar[str] = "assistant.draft_not_found"

    def __init__(self) -> None:
        super().__init__("Draft not found")


class DraftNotPendingError(ConflictError):
    code: ClassVar[str] = "assistant.draft_not_pending"

    def __init__(self) -> None:
        super().__init__("This draft was already confirmed or discarded")


class DuplicateMessageError(ConflictError):
    code: ClassVar[str] = "assistant.duplicate_message"

    def __init__(self) -> None:
        super().__init__("This message was already received")


class AgentUnavailableError(DomainError):
    """The model provider failed (timeout, overload, network). Nothing was charged."""

    code: ClassVar[str] = "assistant.upstream_unavailable"
    http_status: ClassVar[int] = 503

    def __init__(self) -> None:
        super().__init__("The assistant is unavailable right now, try again")


class AgentProtocolError(DomainError):
    """The model replied in a shape we could not turn into blocks."""

    code: ClassVar[str] = "assistant.agent_protocol"
    http_status: ClassVar[int] = 502

    def __init__(self) -> None:
        super().__init__("The assistant produced an unusable reply")
