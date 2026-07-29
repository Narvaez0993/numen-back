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


class InvalidDebtError(ValidationError):
    code: ClassVar[str] = "debts.invalid"
