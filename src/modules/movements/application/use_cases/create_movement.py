from dataclasses import dataclass

from src.modules.movements.application.dto.movement import MovementDTO
from src.modules.movements.application.dto.movement_commands import CreateMovementInputDTO
from src.modules.movements.application.ports.idempotency_store import (
    IdempotencyConflictError,
    IdempotencyStore,
)
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
    ensure_captured_via,
    ensure_not_future,
    ensure_occurred_on,
    ensure_shape,
    ensure_type,
)
from src.shared.application.ports.clock import Clock
from src.shared.application.ports.unit_of_work import UnitOfWork


@dataclass
class CreateMovementUseCase:
    """Registers a movement and moves the money it represents, atomically.

    The write is all-or-nothing on purpose: a card payment that lowered the debt
    but not the account balance would be a ledger that lies. Validation happens
    before the transaction so the atomic part is only writes.
    """

    movement_repository: MovementRepository
    source_ledger: SourceLedger
    references: MovementReferences
    idempotency_store: IdempotencyStore
    unit_of_work: UnitOfWork
    clock: Clock

    async def execute(self, input_dto: CreateMovementInputDTO) -> MovementDTO:
        if input_dto.idempotency_key:
            replayed = await self._replay(input_dto)
            if replayed is not None:
                return replayed

        movement = await self._build(input_dto)

        async def apply() -> MovementDTO:
            if input_dto.idempotency_key:
                await self.idempotency_store.reserve(
                    input_dto.user_id, input_dto.idempotency_key, movement.id
                )
            await self.movement_repository.save(movement)
            for ref, delta in movement.deltas():
                await self.source_ledger.apply_delta(input_dto.user_id, ref, delta)
            return MovementDTO.from_domain(movement)

        try:
            return await self.unit_of_work.atomic(apply)
        except IdempotencyConflictError:
            # A concurrent request with the same key won the race: nothing of ours
            # was committed, so answer with theirs.
            replayed = await self._replay(input_dto)
            if replayed is None:
                raise
            return replayed

    async def _build(self, input_dto: CreateMovementInputDTO) -> Movement:
        movement_type = ensure_type(input_dto.type)
        source = build_source_ref(input_dto.source_type, input_dto.source_id)
        destination = self._build_destination(input_dto)
        ensure_shape(movement_type, source, destination, input_dto.category_id)

        await self.references.ensure_sources(
            input_dto.user_id, input_dto.currency, source, destination
        )
        await self.references.ensure_category(
            input_dto.user_id, input_dto.category_id, movement_type
        )

        occurred_on = ensure_not_future(
            ensure_occurred_on(input_dto.occurred_on), self.clock.now().date()
        )
        return Movement.create(
            user_id=input_dto.user_id,
            type=movement_type,
            description=clean_description(input_dto.description),
            amount=ensure_amount(input_dto.amount),
            currency=input_dto.currency,
            source=source,
            destination=destination,
            category_id=input_dto.category_id,
            occurred_on=occurred_on,
            captured_via=ensure_captured_via(input_dto.captured_via),
            created_at=self.clock.now(),
            subscription_id=input_dto.subscription_id,
        )

    @staticmethod
    def _build_destination(input_dto: CreateMovementInputDTO) -> SourceRef | None:
        if input_dto.destination_type is None and input_dto.destination_id is None:
            return None
        if input_dto.destination_type is None or input_dto.destination_id is None:
            raise InvalidMovementError("A destination needs both its type and its id")
        return build_source_ref(input_dto.destination_type, input_dto.destination_id)

    async def _replay(self, input_dto: CreateMovementInputDTO) -> MovementDTO | None:
        assert input_dto.idempotency_key is not None
        movement_id = await self.idempotency_store.find(
            input_dto.user_id, input_dto.idempotency_key
        )
        if movement_id is None:
            return None
        existing = await self.movement_repository.find(input_dto.user_id, movement_id)
        if existing is None:
            # The key outlived its movement (deleted meanwhile): nothing to replay.
            raise MovementNotFoundError()
        return MovementDTO.from_domain(existing)
