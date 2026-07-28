"""Cost math for the action log — pure, so the guardrail is testable.

Cache reads bill at 10% of input, cache writes at 125% (the provider's standard
multipliers). Prices come from Settings so a pricing change is config, not code.
"""

from dataclasses import dataclass

from src.modules.assistant.application.ports.agent_model import TokenUsage

CACHE_READ_FACTOR = 0.1
CACHE_WRITE_FACTOR = 1.25


@dataclass(frozen=True)
class ModelPricing:
    input_usd_per_mtok: float
    output_usd_per_mtok: float

    def cost_usd(self, usage: TokenUsage) -> float:
        input_cost = usage.input_tokens * self.input_usd_per_mtok
        output_cost = usage.output_tokens * self.output_usd_per_mtok
        cache_read_cost = usage.cache_read_tokens * self.input_usd_per_mtok * CACHE_READ_FACTOR
        cache_write_cost = usage.cache_write_tokens * self.input_usd_per_mtok * CACHE_WRITE_FACTOR
        return (input_cost + output_cost + cache_read_cost + cache_write_cost) / 1_000_000


@dataclass(frozen=True)
class PlanLimits:
    """The two flat counters per tier (docs 02 §10), plus the nudge window."""

    registrations_free: int
    registrations_plus: int
    messages_free: int
    messages_plus: int
    message_grace: int

    def registrations_for(self, tier: str) -> int:
        return self.registrations_plus if tier == "plus" else self.registrations_free

    def messages_for(self, tier: str) -> int:
        return self.messages_plus if tier == "plus" else self.messages_free
