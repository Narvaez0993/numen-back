from typing import ClassVar

from src.shared.domain.errors import NotFoundError, ValidationError


class DebtNotFoundError(NotFoundError):
    code: ClassVar[str] = "debts.not_found"

    def __init__(self) -> None:
        super().__init__("Debt not found")


class CounterpartyNotFoundError(ValidationError):
    code: ClassVar[str] = "debts.counterparty_not_found"

    def __init__(self) -> None:
        super().__init__("That person does not exist")


class OverpaidError(ValidationError):
    code: ClassVar[str] = "debts.overpaid"

    def __init__(self) -> None:
        # Its own code, not a generic `invalid`: paying more than is owed is the one
        # money mistake this ledger can catch, and the client wants to say it plainly.
        super().__init__("That payment is more than what is owed")


class NotWritableOffError(ValidationError):
    code: ClassVar[str] = "debts.not_writable_off"

    def __init__(self) -> None:
        # You write off a claim, not a liability. Being forgiven what you owe is a
        # windfall, not a loss — a different story this app does not tell yet.
        super().__init__("Only money owed to you can be written off")


class AlreadyWrittenOffError(ValidationError):
    code: ClassVar[str] = "debts.already_written_off"

    def __init__(self) -> None:
        super().__init__("That debt was already written off")


class NotWrittenOffError(ValidationError):
    code: ClassVar[str] = "debts.not_written_off"

    def __init__(self) -> None:
        super().__init__("That debt is not written off")


class InvalidDebtError(ValidationError):
    code: ClassVar[str] = "debts.invalid"
