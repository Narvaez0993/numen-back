from structlog import get_logger

_logger = get_logger(__name__)


class LoggingEmailSender:
    """`EmailSender` for the dev phase: logs instead of sending.

    Swap for an SMTP/Resend adapter behind the same port to enable real
    delivery without touching any use case.
    """

    async def send_verification_code(self, email: str, code: str) -> None:
        _logger.info("verification_code_issued", email=email, code=code)
