from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query

from src.modules.overview.adapters.inbound.http.schemas import HomeOverviewResponse
from src.modules.overview.application.dto.home_overview import HomeOverviewInputDTO
from src.modules.overview.application.use_cases.get_home_overview import (
    GetHomeOverviewUseCase,
)
from src.shared.adapters.inbound.http.dependencies import CallerContext, get_caller
from src.shared.domain.errors import ValidationError

router = APIRouter(prefix="/home", tags=["home"])


def _depends_home_use_case() -> GetHomeOverviewUseCase:
    from src.core.di.container import get_container

    return get_container().get_home_overview_use_case


def _resolve_today(raw: str | None) -> str:
    """The client's local day wins over the server's UTC date.

    Without it, "spent today" and "days left" are off for a few hours a day for
    anyone far from UTC — and the app is global-first.
    """
    if raw is None:
        return datetime.now(UTC).date().isoformat()
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValidationError(f"Invalid date: {raw} (expected YYYY-MM-DD)") from exc


@router.get("/overview", response_model=HomeOverviewResponse)
async def home_overview(
    today: str | None = Query(default=None),
    caller: CallerContext = Depends(get_caller),
    use_case: GetHomeOverviewUseCase = Depends(_depends_home_use_case),
) -> HomeOverviewResponse:
    """The whole Home screen in one read: position, month, daily figure and recents."""
    output = await use_case.execute(
        HomeOverviewInputDTO(
            user_id=caller.user_id,
            currency=caller.currency,
            today=_resolve_today(today),
        )
    )
    return HomeOverviewResponse(**output.model_dump())
