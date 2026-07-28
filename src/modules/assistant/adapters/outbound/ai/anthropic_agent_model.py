"""The Anthropic adapter — the only file in the codebase that imports the SDK.

Translation happens at this boundary in both directions: port dataclasses become
SDK params, SDK responses become a `ModelTurn`, and SDK failures become
`AgentUnavailableError` (nothing was charged; the use case logs the tokens).

Caching layout (the margin depends on it): tools render first with a cache
breakpoint on the last tool, the system prompt (static per language) carries the
second, and the last content block of the request carries the third so the
iterations of one turn's loop reuse the growing prefix. Everything volatile
travels in the last user message, where it invalidates nothing.

Thinking stays adaptive except on the forced final call (`tool_choice` and
thinking do not mix). Thinking blocks the model emits are round-tripped through
the port's opaque `provider_state` — the API rejects a tool continuation whose
previous turn lost them.
"""

import json
from collections.abc import Sequence
from typing import Any, Literal, cast

import anthropic
from anthropic.types import (
    CacheControlEphemeralParam,
    MessageParam,
    TextBlock,
    TextBlockParam,
    ToolParam,
    ToolResultBlockParam,
    ToolUseBlock,
    ToolUseBlockParam,
)

from src.modules.assistant.application.ports.agent_model import (
    ModelMessage,
    ModelTurn,
    TokenUsage,
    ToolCall,
    ToolSpec,
)
from src.modules.assistant.domain.errors import AgentProtocolError, AgentUnavailableError

_CACHE = CacheControlEphemeralParam(type="ephemeral")

_STOP_REASONS: dict[str | None, Literal["tool_use", "end_turn", "max_tokens", "refusal"]] = {
    "tool_use": "tool_use",
    "end_turn": "end_turn",
    "stop_sequence": "end_turn",
    "pause_turn": "end_turn",
    "max_tokens": "max_tokens",
    "refusal": "refusal",
    None: "end_turn",
}


class AnthropicAgentModel:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        max_tokens: int,
        effort: str,
        timeout_seconds: float = 45.0,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key, timeout=timeout_seconds, max_retries=1
        )
        self._model = model
        self._max_tokens = max_tokens
        self._effort = effort

    async def respond(
        self,
        *,
        system: str,
        messages: Sequence[ModelMessage],
        tools: Sequence[ToolSpec],
        force_tool: str | None = None,
    ) -> ModelTurn:
        sdk_tools = [_to_tool_param(spec) for spec in tools]
        if sdk_tools:
            sdk_tools[-1]["cache_control"] = _CACHE
        system_blocks = [TextBlockParam(type="text", text=system, cache_control=_CACHE)]
        sdk_messages = [_to_message_param(message) for message in messages]
        _mark_loop_breakpoint(sdk_messages)

        extra: dict[str, Any] = (
            {"tool_choice": {"type": "tool", "name": force_tool}, "thinking": {"type": "disabled"}}
            if force_tool is not None
            else {"output_config": {"effort": self._effort}}
        )
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_blocks,
                messages=sdk_messages,
                tools=sdk_tools,
                **extra,
            )
        except anthropic.APIError as exc:
            raise AgentUnavailableError() from exc

        text = "".join(block.text for block in response.content if isinstance(block, TextBlock))
        tool_calls = tuple(
            ToolCall(id=block.id, name=block.name, arguments=_arguments_of(block))
            for block in response.content
            if isinstance(block, ToolUseBlock)
        )
        opaque = [
            block.model_dump(mode="json")
            for block in response.content
            if block.type in ("thinking", "redacted_thinking")
        ]
        return ModelTurn(
            text=text,
            tool_calls=tool_calls,
            stop_reason=_STOP_REASONS.get(response.stop_reason, "end_turn"),
            usage=TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cache_read_tokens=response.usage.cache_read_input_tokens or 0,
                cache_write_tokens=response.usage.cache_creation_input_tokens or 0,
            ),
            model=response.model,
            provider_state=json.dumps(opaque) if opaque else None,
        )


def _arguments_of(block: ToolUseBlock) -> dict[str, Any]:
    if isinstance(block.input, dict):
        return cast(dict[str, Any], block.input)
    raise AgentProtocolError()


def _to_tool_param(spec: ToolSpec) -> ToolParam:
    return ToolParam(name=spec.name, description=spec.description, input_schema=spec.input_schema)


def _to_message_param(message: ModelMessage) -> MessageParam:
    content: list[Any] = []
    if message.role == "user" and message.tool_results:
        content = [
            ToolResultBlockParam(
                type="tool_result",
                tool_use_id=result.tool_call_id,
                content=result.content,
                is_error=result.is_error,
            )
            for result in message.tool_results
        ]
    elif message.role == "user":
        content = [TextBlockParam(type="text", text=message.text or "")]
    else:
        if message.provider_state is not None:
            content.extend(json.loads(message.provider_state))
        if message.text:
            content.append(TextBlockParam(type="text", text=message.text))
        content.extend(
            ToolUseBlockParam(type="tool_use", id=call.id, name=call.name, input=call.arguments)
            for call in message.tool_calls
        )
    return MessageParam(role=message.role, content=content)


def _mark_loop_breakpoint(messages: list[MessageParam]) -> None:
    """Cache breakpoint on the request's last content block: iterations of the
    same turn re-read the growing prefix instead of re-paying it."""
    if not messages:
        return
    content = messages[-1]["content"]
    if isinstance(content, list) and content:
        last = content[-1]
        if isinstance(last, dict) and last.get("type") in ("text", "tool_result"):
            last["cache_control"] = _CACHE
