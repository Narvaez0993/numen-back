"""Aplicar una jugada: the proposed move becomes a real object, exactly once.

The claim (`proposed → applying`) is one conditional Mongo write, so a double
tap loses the race and gets the current state back — a 200, not an error.
Execution failures are STATE, not HTTP: the play lands as `failed` with a code
the client can name (plan_limit → upsell), and the response is still 200 with
the whole output. HTTP errors are reserved for "that play isn't there" (404),
"that play is not a button" (409) and "pick an account first" (422).

Accepted v1 risk: a crash between claim and finalize strands the play in
`applying`. We do NOT re-claim stale plays — a contribute is a real transfer,
and running it twice is worse than a stuck row.
"""

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel

from src.modules.assistant.application.dto.outputs import AgentOutputDTO
from src.modules.assistant.application.ports.agent_output_repository import (
    AgentOutputRepository,
)
from src.modules.assistant.application.ports.budget_writer import BudgetWriter
from src.modules.assistant.application.ports.goal_contributor import GoalContributor
from src.modules.assistant.domain.entities.agent_output import (
    PLAY_APPLIED,
    PLAY_APPLYING,
    PLAY_FAILED,
    PLAY_PROPOSED,
    AgentOutput,
    Play,
)
from src.modules.assistant.domain.errors import (
    AccountRequiredError,
    AgentOutputNotFoundError,
    PlayExecutionError,
    PlayNotApplyableError,
    PlayNotFoundError,
)
from src.shared.application.ports.clock import Clock


class ApplyPlayInputDTO(BaseModel):
    user_id: UUID
    tier: str
    currency: str
    today: str
    output_id: str
    play_id: str
    account_id: str | None = None


@dataclass
class ApplyPlayUseCase:
    outputs: AgentOutputRepository
    budget_writer: BudgetWriter
    goal_contributor: GoalContributor
    clock: Clock

    async def execute(self, input_dto: ApplyPlayInputDTO) -> AgentOutputDTO:
        output = await self.outputs.find(input_dto.user_id, input_dto.output_id)
        if output is None:
            raise AgentOutputNotFoundError()
        play = output.play(input_dto.play_id)
        if play is None:
            raise PlayNotFoundError()
        if not play.applyable:
            raise PlayNotApplyableError()
        if play.action == "contribute_goal" and not input_dto.account_id:
            raise AccountRequiredError()

        claimed = await self.outputs.transition_play(
            input_dto.user_id,
            input_dto.output_id,
            input_dto.play_id,
            from_status=PLAY_PROPOSED,
            to_status=PLAY_APPLYING,
        )
        if claimed is None:
            return self._lost_claim(await self._refetch(input_dto), input_dto.play_id)

        current = claimed.play(input_dto.play_id)
        if current is None:  # unreachable: the claim just matched it by id
            raise PlayNotFoundError()
        try:
            result_id = await self._dispatch(current, input_dto)
        except PlayExecutionError as failure:
            failed = await self.outputs.transition_play(
                input_dto.user_id,
                input_dto.output_id,
                input_dto.play_id,
                from_status=PLAY_APPLYING,
                to_status=PLAY_FAILED,
                failure_code=failure.code,
            )
            return AgentOutputDTO.from_domain(failed or claimed)

        applied = await self.outputs.transition_play(
            input_dto.user_id,
            input_dto.output_id,
            input_dto.play_id,
            from_status=PLAY_APPLYING,
            to_status=PLAY_APPLIED,
            result_id=result_id,
            applied_at=self.clock.now(),
        )
        return AgentOutputDTO.from_domain(applied or claimed)

    async def _dispatch(self, play: Play, input_dto: ApplyPlayInputDTO) -> str | None:
        """Executes by action. Create-vs-update was decided at composition —
        this only routes params the DTO layer already validated."""
        params = play.params
        if play.action == "set_category_cap":
            return await self.budget_writer.create_cap(
                input_dto.user_id,
                tier=input_dto.tier,
                today=input_dto.today,
                scope="category",
                category_id=str(params["category_id"]),
                target=int(params["target"]),
            )
        if play.action == "raise_category_cap":
            return await self.budget_writer.raise_cap(
                input_dto.user_id,
                today=input_dto.today,
                budget_id=str(params["budget_id"]),
                target=int(params["target"]),
            )
        if play.action == "set_month_cap":
            return await self.budget_writer.create_cap(
                input_dto.user_id,
                tier=input_dto.tier,
                today=input_dto.today,
                scope="global",
                category_id=None,
                target=int(params["target"]),
            )
        if play.action == "contribute_goal":
            await self.goal_contributor.contribute(
                input_dto.user_id,
                currency=input_dto.currency,
                today=input_dto.today,
                goal_id=str(params["goal_id"]),
                account_id=str(input_dto.account_id),
                amount=int(params["amount"]),
            )
            # The transfer IS the record — there is no budget-like id to keep.
            return None
        raise PlayNotApplyableError()

    async def _refetch(self, input_dto: ApplyPlayInputDTO) -> AgentOutput:
        output = await self.outputs.find(input_dto.user_id, input_dto.output_id)
        if output is None:
            raise AgentOutputNotFoundError()
        return output

    @staticmethod
    def _lost_claim(now: AgentOutput, play_id: str) -> AgentOutputDTO:
        """The double tap: whoever got there first is mid-flight or done —
        answer 200 with the truth. Anything else (dismissed, failed) is a
        state this tap cannot act on."""
        play = now.play(play_id)
        if play is not None and play.status in (PLAY_APPLYING, PLAY_APPLIED):
            return AgentOutputDTO.from_domain(now)
        raise PlayNotApplyableError()
