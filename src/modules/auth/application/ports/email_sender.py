from typing import Protocol


class EmailSender(Protocol):
    """Outbound port: delivers transactional emails.

    Sending is suspended for now; the dev adapter logs instead of sending.
    """

    async def send_verification_code(self, email: str, code: str) -> None: ...
