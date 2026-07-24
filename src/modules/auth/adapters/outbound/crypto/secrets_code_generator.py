import secrets
from dataclasses import dataclass


@dataclass
class SecretsCodeGenerator:
    """`CodeGenerator` producing a zero-padded numeric code via `secrets`."""

    length: int

    def generate(self) -> str:
        upper_bound = 10**self.length
        return f"{secrets.randbelow(upper_bound):0{self.length}d}"
