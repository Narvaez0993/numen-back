"""The block union — one schema that the model, storage and HTTP all obey."""

import pytest
from pydantic import ValidationError

from src.modules.assistant.application.dto.blocks import (
    MAX_BLOCKS_PER_MESSAGE,
    RespondWithBlocksInput,
)


def test_every_block_kind_validates() -> None:
    parsed = RespondWithBlocksInput.model_validate(
        {
            "blocks": [
                {"type": "text", "text": "Vas bien este mes."},
                {"type": "stat", "label": "Gastado", "value": "$1.250.000", "amount": 1_250_000},
                {
                    "type": "chart",
                    "kind": "bars",
                    "title": "Por semana",
                    "points": [{"label": "S1", "value": 300}, {"label": "S2", "value": 500}],
                },
                {"type": "navigate", "label": "Ver presupuestos", "route": "/budgets"},
                {"type": "draft", "draft_id": "d-1"},
            ]
        }
    )
    assert [block.type for block in parsed.blocks] == [
        "text",
        "stat",
        "chart",
        "navigate",
        "draft",
    ]


def test_a_route_outside_the_allowlist_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Route not allowed"):
        RespondWithBlocksInput.model_validate(
            {"blocks": [{"type": "navigate", "label": "x", "route": "https://evil.example"}]}
        )


def test_an_unknown_block_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RespondWithBlocksInput.model_validate({"blocks": [{"type": "html", "html": "<b>"}]})


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RespondWithBlocksInput.model_validate(
            {"blocks": [{"type": "text", "text": "hola", "sneaky": True}]}
        )


def test_the_message_has_a_block_budget() -> None:
    blocks = [{"type": "text", "text": f"b{i}"} for i in range(MAX_BLOCKS_PER_MESSAGE + 1)]
    with pytest.raises(ValidationError):
        RespondWithBlocksInput.model_validate({"blocks": blocks})


def test_the_tool_schema_is_a_plain_json_schema() -> None:
    schema = RespondWithBlocksInput.model_json_schema()
    assert schema["type"] == "object"
    assert "blocks" in schema["properties"]
