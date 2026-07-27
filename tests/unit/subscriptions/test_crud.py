from uuid import uuid4

import pytest

from src.modules.subscriptions.application.dto.subscription_commands import (
    CreateSubscriptionInputDTO,
    DeleteSubscriptionInputDTO,
    ListSubscriptionsInputDTO,
    UpdateSubscriptionInputDTO,
)
from src.modules.subscriptions.application.services.subscription_references import (
    SubscriptionReferences,
)
from src.modules.subscriptions.application.use_cases.create_subscription import (
    CreateSubscriptionUseCase,
)
from src.modules.subscriptions.application.use_cases.delete_subscription import (
    DeleteSubscriptionUseCase,
)
from src.modules.subscriptions.application.use_cases.list_subscriptions import (
    ListSubscriptionsUseCase,
)
from src.modules.subscriptions.application.use_cases.update_subscription import (
    UpdateSubscriptionUseCase,
)
from src.modules.subscriptions.domain.errors import (
    InvalidSubscriptionError,
    SubscriptionCategoryNotFoundError,
    SubscriptionNotFoundError,
    SubscriptionSourceCurrencyMismatchError,
    SubscriptionSourceNotFoundError,
)

from .fakes import (
    ACCOUNT,
    CARD,
    CURRENCY,
    TODAY,
    FakeCategoryReader,
    FakeSourceReader,
    FakeSubscriptionRepository,
    FixedClock,
    subscription,
)


def build(repository: FakeSubscriptionRepository | None = None, **overrides: object):
    repo = repository or FakeSubscriptionRepository()
    references = SubscriptionReferences(
        source_reader=overrides.get("source_reader") or FakeSourceReader(),  # type: ignore[arg-type]
        category_reader=overrides.get("category_reader") or FakeCategoryReader(),  # type: ignore[arg-type]
    )
    return (
        repo,
        CreateSubscriptionUseCase(
            subscription_repository=repo, references=references, clock=FixedClock()
        ),
        UpdateSubscriptionUseCase(subscription_repository=repo, references=references),
        DeleteSubscriptionUseCase(subscription_repository=repo),
        ListSubscriptionsUseCase(subscription_repository=repo),
    )


def create_input(**overrides: object) -> CreateSubscriptionInputDTO:
    payload = {
        "user_id": uuid4(),
        "currency": CURRENCY,
        "today": TODAY,
        "name": "Netflix",
        "amount": 30_900,
        "frequency": "monthly",
        "first_charge_on": "2026-07-28",
        "source_type": "account",
        "source_id": ACCOUNT.id,
        "category_id": "subs",
    }
    payload.update(overrides)
    return CreateSubscriptionInputDTO(**payload)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_creating_a_subscription_stores_it_active_with_its_next_charge() -> None:
    repo, create, _, _, _ = build()

    output = await create.execute(create_input())

    assert output.active is True
    assert output.next_charge_on == "2026-07-28"
    assert output.currency == CURRENCY
    assert len(repo.subscriptions) == 1


@pytest.mark.asyncio
async def test_a_charge_can_be_taken_from_a_credit_card() -> None:
    """Most subscriptions are: the model must not assume a debit account."""
    _, create, _, _, _ = build()

    output = await create.execute(create_input(source_type="credit_card", source_id=CARD.id))

    assert (output.source_type, output.source_id) == ("credit_card", CARD.id)


@pytest.mark.asyncio
async def test_icon_and_color_fall_back_to_the_subscriptions_defaults() -> None:
    _, create, _, _, _ = build()

    output = await create.execute(create_input(icon=None, color=None))

    assert (output.icon, output.color) == ("refresh", "amber")


@pytest.mark.asyncio
async def test_an_unknown_source_is_refused() -> None:
    _, create, _, _, _ = build()

    with pytest.raises(SubscriptionSourceNotFoundError):
        await create.execute(create_input(source_id="ghost"))


@pytest.mark.asyncio
async def test_an_unknown_category_is_refused() -> None:
    _, create, _, _, _ = build()

    with pytest.raises(SubscriptionCategoryNotFoundError):
        await create.execute(create_input(category_id="ghost"))


@pytest.mark.asyncio
async def test_a_source_in_another_currency_is_refused() -> None:
    """Its own error: the account and the home currency disagree, and no field in the
    form fixes that — the message has to say what is actually wrong."""
    _, create, _, _, _ = build(source_reader=FakeSourceReader(currency="USD"))

    with pytest.raises(SubscriptionSourceCurrencyMismatchError):
        await create.execute(create_input())


@pytest.mark.asyncio
async def test_an_unknown_frequency_is_refused() -> None:
    _, create, _, _, _ = build()

    with pytest.raises(InvalidSubscriptionError):
        await create.execute(create_input(frequency="fortnightly"))


@pytest.mark.asyncio
async def test_pausing_is_an_edit_that_stops_the_next_charge() -> None:
    sub = subscription()
    repo, _, update, _, _ = build(FakeSubscriptionRepository([sub]))

    output = await update.execute(
        UpdateSubscriptionInputDTO(
            user_id=sub.user_id,
            currency=CURRENCY,
            today=TODAY,
            subscription_id=sub.id,
            active=False,
        )
    )

    assert output.active is False
    assert output.next_charge_on is None
    assert repo.subscriptions[0].active is False


@pytest.mark.asyncio
async def test_an_absent_field_keeps_its_stored_value() -> None:
    sub = subscription(name="Netflix", amount=30_900)
    _, _, update, _, _ = build(FakeSubscriptionRepository([sub]))

    output = await update.execute(
        UpdateSubscriptionInputDTO(
            user_id=sub.user_id,
            currency=CURRENCY,
            today=TODAY,
            subscription_id=sub.id,
            amount=44_900,
        )
    )

    assert (output.name, output.amount) == ("Netflix", 44_900)
    assert output.first_charge_on == sub.first_charge_on


@pytest.mark.asyncio
async def test_editing_someone_elses_subscription_is_a_not_found() -> None:
    sub = subscription()
    _, _, update, _, _ = build(FakeSubscriptionRepository([sub]))

    with pytest.raises(SubscriptionNotFoundError):
        await update.execute(
            UpdateSubscriptionInputDTO(
                user_id=uuid4(),
                currency=CURRENCY,
                today=TODAY,
                subscription_id=sub.id,
                amount=1,
            )
        )


@pytest.mark.asyncio
async def test_deleting_a_missing_subscription_is_a_not_found() -> None:
    _, _, _, delete, _ = build()

    with pytest.raises(SubscriptionNotFoundError):
        await delete.execute(DeleteSubscriptionInputDTO(user_id=uuid4(), subscription_id="ghost"))


@pytest.mark.asyncio
async def test_the_totals_count_what_is_running_and_list_what_exists() -> None:
    """A paused subscription is still shown — you just are not paying for it."""
    user_id = uuid4()
    repo = FakeSubscriptionRepository(
        [
            subscription(user_id=user_id, amount=30_900, frequency="monthly"),
            subscription(user_id=user_id, amount=120_000, frequency="yearly"),
            subscription(user_id=user_id, amount=99_000, frequency="monthly", active=False),
        ]
    )
    _, _, _, _, list_subs = build(repo)

    output = await list_subs.execute(
        ListSubscriptionsInputDTO(user_id=user_id, currency=CURRENCY, today=TODAY)
    )

    assert len(output.subscriptions) == 3
    assert output.count == 2
    assert output.monthly == 30_900 + 10_000
    assert output.yearly == 370_800 + 120_000


@pytest.mark.asyncio
async def test_the_list_is_tenant_scoped() -> None:
    mine, theirs = uuid4(), uuid4()
    repo = FakeSubscriptionRepository([subscription(user_id=mine), subscription(user_id=theirs)])
    _, _, _, _, list_subs = build(repo)

    output = await list_subs.execute(
        ListSubscriptionsInputDTO(user_id=mine, currency=CURRENCY, today=TODAY)
    )

    assert len(output.subscriptions) == 1
