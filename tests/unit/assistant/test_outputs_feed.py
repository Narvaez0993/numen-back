"""Outputs in the feed (the vigentes) and the shelf/read/dismiss lifecycle."""

from datetime import UTC, datetime

import pytest

from src.modules.assistant.application.use_cases.dismiss_output import (
    DismissOutputInputDTO,
    DismissOutputUseCase,
)
from src.modules.assistant.application.use_cases.get_output import (
    GetOutputInputDTO,
    GetOutputUseCase,
)
from src.modules.assistant.application.use_cases.list_outputs import (
    ListOutputsInputDTO,
    ListOutputsUseCase,
)
from src.modules.assistant.application.use_cases.mark_output_read import (
    MarkOutputReadInputDTO,
    MarkOutputReadUseCase,
)
from src.modules.assistant.domain.entities.agent_output import WEEKLY_REVIEW
from src.modules.assistant.domain.errors import AgentOutputNotFoundError

from .fakes import USER_ID, FakeAgentOutputRepository, agent_output
from .test_feed_insights import feed_input, use_case

NOW = datetime(2026, 7, 28, 12, 0, 0, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


def weekly(created_at: datetime, period: str = "2026-W30") -> object:
    return agent_output(
        kind=WEEKLY_REVIEW,
        period=period,
        payload={"diagnosis_text": "x"},
        plays=(),
        created_at=created_at,
    )


@pytest.mark.asyncio
async def test_feed_carries_the_latest_corte_and_a_fresh_weekly() -> None:
    outputs = FakeAgentOutputRepository()
    old = agent_output(period="2026-05", created_at=datetime(2026, 6, 1, tzinfo=UTC))
    new = agent_output(period="2026-06", created_at=datetime(2026, 7, 1, tzinfo=UTC))
    await outputs.add(old)
    await outputs.add(new)
    await outputs.add(weekly(datetime(2026, 7, 27, tzinfo=UTC)))
    case, _ = use_case(outputs=outputs)

    feed = await case.execute(feed_input())

    monthly = next(o for o in feed.outputs if o.kind == "monthly_summary")
    assert monthly.id == new.id  # the latest reigns; May's Corte lives on the shelf
    assert {o.kind for o in feed.outputs} == {"monthly_summary", "weekly_review"}
    assert feed.unseen_count == 2


@pytest.mark.asyncio
async def test_a_stale_weekly_leaves_the_feed() -> None:
    outputs = FakeAgentOutputRepository()
    await outputs.add(weekly(datetime(2026, 7, 10, tzinfo=UTC)))  # 18 days before TODAY
    case, _ = use_case(outputs=outputs)

    feed = await case.execute(feed_input())

    assert feed.outputs == []
    assert feed.unseen_count == 0


@pytest.mark.asyncio
async def test_dismissed_leaves_the_feed_but_never_the_shelf() -> None:
    outputs = FakeAgentOutputRepository()
    corte = agent_output()
    await outputs.add(corte)
    await DismissOutputUseCase(outputs=outputs, clock=FixedClock()).execute(
        DismissOutputInputDTO(user_id=USER_ID, output_id=corte.id)
    )
    case, _ = use_case(outputs=outputs)

    feed = await case.execute(feed_input())
    shelf = await ListOutputsUseCase(outputs=outputs).execute(ListOutputsInputDTO(user_id=USER_ID))

    assert feed.outputs == []
    assert [o.id for o in shelf.outputs] == [corte.id]
    assert shelf.outputs[0].dismissed_at is not None


@pytest.mark.asyncio
async def test_read_is_written_once_and_missing_ids_404() -> None:
    outputs = FakeAgentOutputRepository()
    corte = agent_output()
    await outputs.add(corte)
    read = MarkOutputReadUseCase(outputs=outputs, clock=FixedClock())

    first = await read.execute(MarkOutputReadInputDTO(user_id=USER_ID, output_id=corte.id))
    second = await read.execute(MarkOutputReadInputDTO(user_id=USER_ID, output_id=corte.id))

    assert first.read_at == NOW
    assert second.read_at == NOW
    with pytest.raises(AgentOutputNotFoundError):
        await read.execute(MarkOutputReadInputDTO(user_id=USER_ID, output_id="ghost"))


@pytest.mark.asyncio
async def test_get_output_returns_the_dto_or_404() -> None:
    outputs = FakeAgentOutputRepository()
    corte = agent_output()
    await outputs.add(corte)
    get = GetOutputUseCase(outputs=outputs)

    found = await get.execute(GetOutputInputDTO(user_id=USER_ID, output_id=corte.id))
    assert found.id == corte.id
    assert found.plays[0].action == "set_category_cap"

    with pytest.raises(AgentOutputNotFoundError):
        await get.execute(GetOutputInputDTO(user_id=USER_ID, output_id="ghost"))
