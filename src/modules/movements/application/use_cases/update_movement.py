from dataclasses import dataclass

from src.modules.movements.application.dto.movement import MovementDTO
from src.modules.movements.application.dto.movement_commands import UpdateMovementInputDTO
from src.modules.movements.application.ports.movement_repository import MovementRepository
from src.modules.movements.application.ports.source_ledger import SourceLedger
from src.modules.movements.application.services.movement_references import (
    MovementReferences,
)
from src.modules.movements.domain.entities.movement import Movement, SourceRef
from src.modules.movements.domain.errors import (
    InvalidMovementError,
    MovementNotFoundError,
)
from src.modules.movements.domain.validation import (
    build_source_ref,
    clean_description,
    ensure_amount,
    ensure_not_future,
    ensure_occurred_on,
    ensure_shape,
)
from src.shared.application.ports.clock import Clock
from src.shared.application.ports.unit_of_work import UnitOfWork


@dataclass
class UpdateMovementUseCase:
    """Edits a movement and re-settles the money it had already moved.

    The correction is symmetric: **revert the old deltas, apply the new ones**, in
    one transaction. That is what keeps an edit from double-counting — raising an
    expense from 50k to 80k must leave the account 80k lower, not 130k.
    """

    movement_repository: MovementRepository
    source_ledger: SourceLedger
    references: MovementReferences
    unit_of_work: UnitOfWork
    clock: Clock

    async def execute(self, input_dto: UpdateMovementInputDTO) -> MovementDTO:
        current = await self.movement_repository.find(input_dto.user_id, input_dto.movement_id)
        if current is None:
            raise MovementNotFoundError()

        updated = self._patch(current, input_dto)
        # Coherence is checked on the resulting state, not on the patch: what
        # matters is that the movement still makes sense once merged.
        ensure_shape(updated.type, updated.source, updated.destination, updated.category_id)
        await self.references.ensure_sources(
            input_dto.user_id, updated.currency, updated.source, updated.destination
        )
        await self.references.ensure_category(input_dto.user_id, updated.category_id, updated.type)

        money_moved = current.deltas() != updated.deltas()

        async def apply() -> MovementDTO:
            if money_moved:
                for ref, delta in current.reverted_deltas():
                    await self.source_ledger.apply_delta(input_dto.user_id, ref, delta)
                for ref, delta in updated.deltas():
                    await self.source_ledger.apply_delta(input_dto.user_id, ref, delta)
            await self.movement_repository.save(updated)
            return MovementDTO.from_domain(updated)

        return await self.unit_of_work.atomic(apply)

    def _patch(self, current: Movement, input_dto: UpdateMovementInputDTO) -> Movement:
        occurred_on: str | None = None
        if input_dto.occurred_on is not None:
            occurred_on = ensure_not_future(
                ensure_occurred_on(input_dto.occurred_on), self.clock.now().date()
            )

        return current.with_updates(
            description=(
                None if input_dto.description is None else clean_description(input_dto.description)
            ),
            amount=None if input_dto.amount is None else ensure_amount(input_dto.amount),
            source=self._patched_ref(input_dto.source_type, input_dto.source_id, "Source"),
            destination=self._patched_ref(
                input_dto.destination_type, input_dto.destination_id, "Destination"
            ),
            category_id=input_dto.category_id,
            occurred_on=occurred_on,
        )

    @staticmethod
    def _patched_ref(ref_type: str | None, ref_id: str | None, field: str) -> SourceRef | None:
        if ref_type is None and ref_id is None:
            return None
        if ref_type is None or ref_id is None:
            raise InvalidMovementError(f"{field} needs both its type and its id")
        return build_source_ref(ref_type, ref_id)
