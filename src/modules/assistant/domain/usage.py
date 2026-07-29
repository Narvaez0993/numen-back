"""The consumption policy: what a chat turn costs and when the door closes.

Two flat counters (docs 02 §10): "AI registrations" and "agent messages". Pure
functions so the rules are testable without a database or a model. The month
rollover needs no job — counters are keyed by `(user, period)`, so a new month
simply starts a new row at zero.
"""

from dataclasses import dataclass

from src.modules.assistant.domain.errors import ChatLimitReachedError


@dataclass(frozen=True)
class Consumption:
    registrations: int
    messages: int


def ensure_can_chat(messages_used: int, limit: int, grace: int) -> None:
    """Free users get `grace` messages past the limit — the soft nudge window.

    Inside the window the request is served and the client paints the nudge from
    the usage payload; past it, this raises and the gate takes over.
    """
    if messages_used >= limit + grace:
        raise ChatLimitReachedError()


def registrations_available(registrations_used: int, limit: int) -> bool:
    return registrations_used < limit


def derive_consumption(
    drafts_staged: int,
    *,
    read_tools_used: bool,
    has_data_blocks: bool,
) -> Consumption:
    """What this turn cost, derived from what it actually did.

    A capture costs registrations, one per draft. The courtesy text next to a
    draft does not also cost a message — but if the agent additionally read data
    or answered with data blocks (a mixed turn), that answering half costs one.
    A turn with no draft is a plain answer: one message, even without tools
    (answering from conversation memory is still the agent answering).
    """
    if drafts_staged == 0:
        return Consumption(registrations=0, messages=1)
    answered_too = read_tools_used or has_data_blocks
    return Consumption(registrations=drafts_staged, messages=1 if answered_too else 0)
