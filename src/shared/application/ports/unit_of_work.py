from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar

T = TypeVar("T")


class UnitOfWork(Protocol):
    """Outbound port: run several writes as one all-or-nothing unit.

    The cash-basis flow needs it: a credit-card payment lowers the card debt and
    the account balance, and half of that would be a wrong ledger.

    `operation` may be **re-executed** if the store retries a transient failure,
    so build entities before calling and keep only writes inside — same ids, same
    values, same outcome.
    """

    async def atomic(self, operation: Callable[[], Awaitable[T]]) -> T: ...
