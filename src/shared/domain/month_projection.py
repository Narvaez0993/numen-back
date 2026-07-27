"""Where the month lands if the user keeps spending at their current rate.

One formula for the whole app. Home shows it as the pace (*"a este ritmo cierras en
$2.287.800"*) and Presupuestos shows it against the cap (*"te pasas por $180.000"*) —
if each module carried its own version, the two screens would eventually disagree about
the same month, and the user would be right to trust neither.

The formula it replaced went the other way: the hero divided `(income - spent)` by the
days left and called it "available today". That number had the incentive backwards —
spending nothing today made **tomorrow's** figure bigger, because the same money was
split across fewer days. A projection can only fall when you hold back.
"""

# Under this, a projection is noise: one restaurant bill on the 2nd would forecast a
# month of eating out. Better to say nothing than to alarm someone over a Tuesday.
MIN_DAYS_FOR_PROJECTION = 3


def project(*, spent: int, days_elapsed: int, total_days: int) -> int | None:
    """What the month closes at, at the current rate. `None` while it is too young.

    Takes the **month's length**, not the days left, on purpose: `days_elapsed` and
    `days_left` both include today, so projecting over `days_left` estimated one extra
    day — a 31-day month came out as 32 and the figure was ~4% high in the middle of
    the month. Deriving the remainder here makes that mistake impossible at the caller.

    Only the remaining days are estimated: what was already spent is a fact and is
    carried as-is, so the projection can never contradict the ledger.
    """
    if days_elapsed < MIN_DAYS_FOR_PROJECTION or spent <= 0:
        return None

    remaining = max(0, total_days - days_elapsed)
    return spent + spent * remaining // days_elapsed
