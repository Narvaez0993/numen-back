"""Which figure Home leads with.

`hero = f(objective, data that exists)`: the objective says what is preferred, the data
says what is possible, and a figure is never shown without its data. `invite` is that
last rule made visible — it means "you told us what you came for and we cannot answer it
yet", which is the most useful thing the screen can say.
"""

from src.modules.overview.domain.hero_focus import choose


def test_without_movements_nothing_can_be_said_about_a_month() -> None:
    """The checklist comes first whatever the objective, and even with a cap set: there
    is no pace, no saving and no trend to read from an empty month."""
    for objective in (None, "gastos", "ahorrar", "deudas"):
        assert (
            choose(
                objective=objective,
                has_movements=False,
                card_debt=800_000,
                income=5_000_000,
                has_cap=True,
            )
            == "start"
        )


def test_the_pace_is_the_default_once_there_are_movements() -> None:
    assert (
        choose(objective=None, has_movements=True, card_debt=0, income=0, has_cap=False) == "pace"
    )
    assert (
        choose(objective="gastos", has_movements=True, card_debt=0, income=0, has_cap=False)
        == "pace"
    )


def test_a_cap_replaces_the_bare_pace() -> None:
    """Both describe the month; only the cap is measured against a number the user
    chose."""
    assert (
        choose(objective=None, has_movements=True, card_debt=0, income=0, has_cap=True) == "budget"
    )
    assert (
        choose(objective="gastos", has_movements=True, card_debt=0, income=0, has_cap=True)
        == "budget"
    )


def test_wanting_out_of_debt_leads_with_the_debt() -> None:
    assert (
        choose(objective="deudas", has_movements=True, card_debt=830_900, income=0, has_cap=False)
        == "debt"
    )


def test_the_declared_objective_still_wins_over_a_cap() -> None:
    """Someone who said "salir de deudas" opens the app to see their debt. The cap is
    still in the payload and the client keeps it as a secondary row."""
    assert (
        choose(objective="deudas", has_movements=True, card_debt=830_900, income=0, has_cap=True)
        == "debt"
    )
    assert (
        choose(objective="ahorrar", has_movements=True, card_debt=0, income=5_000_000, has_cap=True)
        == "saving"
    )


def test_wanting_out_of_debt_without_any_debt_asks_for_it() -> None:
    """Not a gap to paper over with a generic number: registering the debt is the whole
    point of what the user said they came for. A cap does not stand in for it either."""
    assert (
        choose(
            objective="deudas",
            has_movements=True,
            card_debt=0,
            income=5_000_000,
            has_cap=True,
        )
        == "invite"
    )


def test_wanting_to_save_leads_with_what_was_saved() -> None:
    assert (
        choose(
            objective="ahorrar",
            has_movements=True,
            card_debt=0,
            income=5_000_000,
            has_cap=False,
        )
        == "saving"
    )


def test_wanting_to_save_without_income_asks_for_it() -> None:
    """`saved` is `income - spent`; without income that is just the spending negated."""
    assert (
        choose(objective="ahorrar", has_movements=True, card_debt=0, income=0, has_cap=False)
        == "invite"
    )


def test_the_objective_wins_over_the_data_it_does_not_need() -> None:
    """Someone paying off debt sees their debt even in a month with income and spending
    — the objective decides the order, not the size of the numbers."""
    assert (
        choose(
            objective="deudas",
            has_movements=True,
            card_debt=100_000,
            income=9_000_000,
            has_cap=False,
        )
        == "debt"
    )
