from typing import Protocol


class CodeGenerator(Protocol):
    """Outbound port: generates a numeric one-time verification code."""

    def generate(self) -> str: ...
