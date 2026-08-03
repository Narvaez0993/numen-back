"""The proactive narrator's tool — separate from the chat's `_SPECS` on purpose.

One STATIC schema means one cacheable prompt prefix per language for the whole
monthly sweep. The items being narrated ride in the volatile user message; this
spec never changes with them. Chat's registry is never touched.
"""

from typing import Final

from src.modules.assistant.application.ports.agent_model import ToolSpec

NARRATE_TOOL: Final[str] = "narrate"

MAX_NARRATION_TEXT: Final[int] = 180

NARRATE_SPECS: Final[tuple[ToolSpec, ...]] = (
    ToolSpec(
        name=NARRATE_TOOL,
        description=(
            "Deliver one short line of narration per item. Cover every item_id "
            "you were given, exactly once."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_id": {"type": "string"},
                            "text": {
                                "type": "string",
                                "maxLength": MAX_NARRATION_TEXT,
                            },
                        },
                        "required": ["item_id", "text"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["items"],
            "additionalProperties": False,
        },
    ),
)
