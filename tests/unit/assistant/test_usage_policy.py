"""The consumption rules — the money side of every chat turn."""

import pytest

from src.modules.assistant.domain.errors import ChatLimitReachedError
from src.modules.assistant.domain.usage import (
    derive_consumption,
    ensure_can_chat,
    registrations_available,
)


def test_a_plain_answer_costs_one_message() -> None:
    consumption = derive_consumption(0, read_tools_used=True, has_data_blocks=True)
    assert (consumption.registrations, consumption.messages) == (0, 1)


def test_answering_from_memory_still_costs_the_message() -> None:
    consumption = derive_consumption(0, read_tools_used=False, has_data_blocks=False)
    assert (consumption.registrations, consumption.messages) == (0, 1)


def test_a_pure_capture_costs_only_the_registration() -> None:
    consumption = derive_consumption(1, read_tools_used=False, has_data_blocks=False)
    assert (consumption.registrations, consumption.messages) == (1, 0)


def test_two_drafts_cost_two_registrations() -> None:
    consumption = derive_consumption(2, read_tools_used=False, has_data_blocks=False)
    assert (consumption.registrations, consumption.messages) == (2, 0)


def test_a_mixed_turn_costs_both() -> None:
    consumption = derive_consumption(1, read_tools_used=True, has_data_blocks=False)
    assert (consumption.registrations, consumption.messages) == (1, 1)


def test_a_capture_with_data_blocks_is_also_mixed() -> None:
    consumption = derive_consumption(1, read_tools_used=False, has_data_blocks=True)
    assert (consumption.registrations, consumption.messages) == (1, 1)


def test_the_gate_serves_the_grace_window() -> None:
    ensure_can_chat(12, limit=10, grace=3)  # 11th..13th message pass


def test_the_gate_closes_after_the_grace() -> None:
    with pytest.raises(ChatLimitReachedError):
        ensure_can_chat(13, limit=10, grace=3)


def test_registrations_availability_is_a_plain_threshold() -> None:
    assert registrations_available(59, 60)
    assert not registrations_available(60, 60)
