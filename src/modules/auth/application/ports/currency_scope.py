from typing import Protocol
from uuid import UUID


class CurrencyScope(Protocol):
    """Outbound port: everything the user's home currency is stamped on.

    The home currency is not just a display setting — every amount the user stores
    is denominated in **its minor unit**, and COP has no decimals while USD has two.
    So the same stored `30000` reads as `$300.00` in USD and `$30.000` in COP:
    changing the currency **moves the decimal point** on data that already exists.

    That makes the change safe in exactly one situation — the user picked the wrong
    currency and has not registered any money yet — and unsafe in the other, where
    it would silently multiply their history by 100. This port answers which one it
    is (`has_history`) and performs the safe case (`restamp`).

    `auth` declares it instead of importing accounts, movements or subscriptions;
    the adapter translates. Same seam as `SourceLedger` in `movements`.
    """

    async def has_history(self, user_id: UUID) -> bool:
        """Has this user registered money that a re-label would misread?"""
        ...

    async def restamp(self, user_id: UUID, currency: str) -> None:
        """Re-label the user's sources and forecasts. **Never converts amounts** —
        there are no exchange rates here, and this is a correction, not a conversion.
        """
        ...
