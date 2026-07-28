"""Outbound port: one turn of a tool-using language model.

The port is a single stateless call; the tool-use LOOP lives in the use case,
which executes tools through the module's own ports and calls `respond` again.
Nothing from any provider SDK crosses this boundary — the adapter translates in
both directions and converts provider failures into `AgentUnavailableError`.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    """Plain JSON Schema — provider-agnostic."""


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    tool_call_id: str
    content: str
    """Already-serialized JSON; the use case owns serialization."""
    is_error: bool = False


@dataclass(frozen=True)
class ModelMessage:
    """One turn of the transcript the use case assembles."""

    role: Literal["user", "assistant"]
    text: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int

    def plus(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_tokens=self.cache_read_tokens + other.cache_read_tokens,
            cache_write_tokens=self.cache_write_tokens + other.cache_write_tokens,
        )


ZERO_USAGE = TokenUsage(input_tokens=0, output_tokens=0, cache_read_tokens=0, cache_write_tokens=0)


@dataclass(frozen=True)
class ModelTurn:
    text: str
    """Concatenated text parts ("" when the model only called tools)."""
    tool_calls: tuple[ToolCall, ...]
    stop_reason: Literal["tool_use", "end_turn", "max_tokens", "refusal"]
    usage: TokenUsage
    model: str


class AgentModel(Protocol):
    async def respond(
        self,
        *,
        system: str,
        messages: Sequence[ModelMessage],
        tools: Sequence[ToolSpec],
        force_tool: str | None = None,
    ) -> ModelTurn: ...
