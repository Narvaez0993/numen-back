from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID, uuid4

from src.modules.assistant.domain.errors import DraftNotPendingError

PENDING = "pending"
CONFIRMED = "confirmed"
DISCARDED = "discarded"

# What the card may change before confirming. Identity (id, user, currency) and
# lifecycle are not overridable — a draft edited into a different user's ledger is
# not an edit.
OVERRIDABLE_FIELDS: frozenset[str] = frozenset(
    {
        # Which debt the abono lands on. Overridable because the capture often does
        # not name a person — "me pagaron 2.000 de una deuda" — and the card asks by
        # showing the user their own open debts.
        "target_debt_id",
        "direction",
        "counterparty_id",
        "counterparty_name",
        "amount",
        "account_id",
        "due_on",
        "note",
    }
)

NEW = "new"
PAYMENT = "payment"
#: What the capture meant. `new` opens a debt; `payment` pays one down.
#:
#: They share this entity because they share everything that matters here — the card,
#: the lifecycle, the store, the confirm and discard endpoints. Only the last step
#: differs. Without `payment`, "Santiago me pagó 2.000" had no tool that fit, and the
#: agent did the closest thing it could: it opened a SECOND debt for Santiago.
DRAFT_KINDS: frozenset[str] = frozenset({NEW, PAYMENT})


@dataclass(frozen=True)
class DebtDraft:
    """A debt the agent understood but the user has not confirmed.

    Its own entity rather than a movement draft with extra fields, because it
    answers different questions: not "which category" but "which person", not
    "expense or income" but "who owes whom". Sharing a shape would have meant a
    card full of fields that never apply.

    Two things the agent is allowed not to know, and the card asks instead:

    * **Who.** The agent hears a name ("Andrés"), not an id. When that name already
      matches someone in the user's ledger the registry fills `counterparty_id`, and
      otherwise the person is created on confirm — the same inline creation the
      manual form does.
    * **Which account.** Lending moves real cash and guessing which account it left
      would be the app deciding for you. `None` is also a legitimate final answer: a
      dinner split moves nothing, because the bill already left as one expense.
    """

    id: str
    user_id: UUID
    currency: str
    kind: str
    """`new` | `payment` — opening a debt, or paying one down."""
    target_debt_id: str | None
    """Which debt is being paid. Set on a `payment` and never on a `new` one: there
    is no debt to point at until the user confirms."""
    direction: str
    """`incoming` = they owe me · `outgoing` = I owe them. On a payment it is the
    target debt's, because which way the cash flows back depends on it."""
    counterparty_id: str | None
    """Filled when the spoken name matched someone already in the ledger."""
    counterparty_name: str
    """What the user called them. Creates the person on confirm when no id matched."""
    amount: int
    """Positive, in the minor unit of `currency`."""
    account_id: str | None
    """The account the cash crossed. `None` until the card asks — and still `None`
    afterwards when the honest answer is that no money moved.

    A **payment** has no such answer: money always changes hands when a debt is paid
    down, so its card offers accounts only."""
    due_on: str | None
    note: str | None
    status: str
    debt_id: str | None
    created_at: datetime
    captured_via: str = "text"
    """How the words reached us (`text` | `voice`) — a fact of the capture context,
    never something the model (or an edit) gets to claim."""

    @property
    def pending(self) -> bool:
        return self.status == PENDING

    @property
    def is_payment(self) -> bool:
        return self.kind == PAYMENT

    @classmethod
    def stage(
        cls,
        *,
        user_id: UUID,
        currency: str,
        direction: str,
        kind: str = NEW,
        target_debt_id: str | None = None,
        counterparty_id: str | None,
        counterparty_name: str,
        amount: int,
        account_id: str | None,
        due_on: str | None,
        note: str | None,
        created_at: datetime,
        captured_via: str = "text",
    ) -> "DebtDraft":
        return cls(
            id=str(uuid4()),
            user_id=user_id,
            currency=currency,
            kind=kind,
            target_debt_id=target_debt_id,
            direction=direction,
            counterparty_id=counterparty_id,
            counterparty_name=" ".join(counterparty_name.split()),
            amount=amount,
            account_id=account_id,
            due_on=due_on,
            note=note,
            status=PENDING,
            debt_id=None,
            created_at=created_at,
            captured_via=captured_via,
        )

    def apply_overrides(self, overrides: dict[str, object]) -> "DebtDraft":
        """The user's edits from the confirm card, applied to a pending draft."""
        self._ensure_pending()
        unknown = set(overrides) - OVERRIDABLE_FIELDS
        if unknown:
            raise ValueError(f"Field(s) not overridable: {sorted(unknown)}")
        return replace(self, **overrides)  # type: ignore[arg-type]

    def confirm(self, debt_id: str) -> "DebtDraft":
        self._ensure_pending()
        return replace(self, status=CONFIRMED, debt_id=debt_id)

    def discard(self) -> "DebtDraft":
        self._ensure_pending()
        return replace(self, status=DISCARDED)

    def _ensure_pending(self) -> None:
        if not self.pending:
            raise DraftNotPendingError()
