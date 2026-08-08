from typing import ClassVar

from src.shared.domain.errors import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


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


class AgentOutputNotFoundError(NotFoundError):
    code: ClassVar[str] = "assistant.output_not_found"

    def __init__(self) -> None:
        super().__init__("Agent output not found")


class PlayNotFoundError(NotFoundError):
    code: ClassVar[str] = "assistant.play_not_found"

    def __init__(self) -> None:
        super().__init__("Play not found in this output")


class PlayNotApplyableError(ConflictError):
    code: ClassVar[str] = "assistant.play_not_applyable"

    def __init__(self) -> None:
        # `treat` is the agent saying "this fits" — advice, not a button.
        super().__init__("This play cannot be applied")


class AccountRequiredError(ValidationError):
    code: ClassVar[str] = "assistant.account_required"

    def __init__(self) -> None:
        # A goal contribution is a real transfer: the user picks where from.
        super().__init__("Pick the account the contribution leaves from")


class PlayExecutionError(Exception):
    """The sibling module said no (gate, gone, duplicate). Never an HTTP error:
    the play lands as `failed` with this code and the response is still 200."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class DraftNotFoundError(NotFoundError):
    code: ClassVar[str] = "assistant.draft_not_found"

    def __init__(self) -> None:
        super().__init__("Draft not found")


class DraftNotPendingError(ConflictError):
    code: ClassVar[str] = "assistant.draft_not_pending"

    def __init__(self) -> None:
        super().__init__("This draft was already confirmed or discarded")


class DebtPaymentAccountRequiredError(ValidationError):
    code: ClassVar[str] = "assistant.debt_payment_account_required"

    def __init__(self) -> None:
        # A loan may honestly have moved no cash; a repayment never can. "No money
        # moved" is not an answer to being paid back, it is a contradiction.
        super().__init__("A debt payment has to name the account the money moves on")


class DebtPaymentTargetRequiredError(ValidationError):
    code: ClassVar[str] = "assistant.debt_payment_target_required"

    def __init__(self) -> None:
        super().__init__("A debt payment has to name the debt it pays down")


class DraftSourceRequiredError(ValidationError):
    code: ClassVar[str] = "assistant.draft_source_required"

    def __init__(self) -> None:
        # The agent is allowed not to know where the money came from — it is not
        # allowed to guess. When the capture never said it and the user owns more
        # than one source, the draft is staged without one and the confirm card
        # asks. Confirming is the point where an answer becomes mandatory.
        super().__init__("Pick the account or card the money moves from")


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
