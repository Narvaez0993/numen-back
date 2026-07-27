"""Which figure Home leads with — the one decision that makes the app feel personal.

The rule is `hero = f(objective, data that exists)`:

- the **objective** the user chose in the onboarding says which figure is *preferred*;
- the **data** they actually have says which figure is *possible*;
- a figure is never shown without its data.

The third bullet is why `invite` exists. Someone who said "salir de deudas" and has no
debt registered is not a gap to paper over with a generic number — asking them to
register it is the single most useful thing the screen can do, and it turns the
intention they already stated into the next action.
"""

from typing import Literal

Focus = Literal["start", "pace", "debt", "saving", "invite"]

OBJECTIVE_DEBT = "deudas"
OBJECTIVE_SAVING = "ahorrar"


def choose(
    *,
    objective: str | None,
    has_movements: bool,
    card_debt: int,
    income: int,
) -> Focus:
    """The rung Home shows. `invite` means "the objective's data is missing".

    Without movements nothing can be said about a month, so the checklist comes first
    regardless of the objective: there is no pace, no saving and no trend to read yet.
    """
    if not has_movements:
        return "start"

    if objective == OBJECTIVE_DEBT:
        return "debt" if card_debt > 0 else "invite"

    if objective == OBJECTIVE_SAVING:
        # Saving is `income - spent`; without income registered that subtraction is
        # just the spending with a minus sign in front of it.
        return "saving" if income > 0 else "invite"

    # "gastos", or no objective at all: the pace is always available once there are
    # movements, which makes it the honest default.
    return "pace"
