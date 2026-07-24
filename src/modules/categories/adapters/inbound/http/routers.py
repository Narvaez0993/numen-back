from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.modules.categories.adapters.inbound.http.schemas import (
    CategoriesListResponse,
    CategoryResponse,
    CreateCategoryRequest,
    UpdateCategoryRequest,
)
from src.modules.categories.application.dto.create_category import CreateCategoryInputDTO
from src.modules.categories.application.dto.delete_category import DeleteCategoryInputDTO
from src.modules.categories.application.dto.list_categories import ListCategoriesInputDTO
from src.modules.categories.application.dto.update_category import UpdateCategoryInputDTO
from src.modules.categories.application.use_cases.create_category import CreateCategoryUseCase
from src.modules.categories.application.use_cases.delete_category import DeleteCategoryUseCase
from src.modules.categories.application.use_cases.list_categories import ListCategoriesUseCase
from src.modules.categories.application.use_cases.update_category import UpdateCategoryUseCase
from src.shared.adapters.inbound.http.dependencies import (
    get_current_tier,
    get_current_user_id,
)

router = APIRouter(prefix="/categories", tags=["categories"])


def _depends_list_use_case() -> ListCategoriesUseCase:
    from src.core.di.container import get_container

    return get_container().list_categories_use_case


def _depends_create_use_case() -> CreateCategoryUseCase:
    from src.core.di.container import get_container

    return get_container().create_category_use_case


def _depends_update_use_case() -> UpdateCategoryUseCase:
    from src.core.di.container import get_container

    return get_container().update_category_use_case


def _depends_delete_use_case() -> DeleteCategoryUseCase:
    from src.core.di.container import get_container

    return get_container().delete_category_use_case


@router.get("", response_model=CategoriesListResponse)
async def list_categories(
    user_id: UUID = Depends(get_current_user_id),
    use_case: ListCategoriesUseCase = Depends(_depends_list_use_case),
) -> CategoriesListResponse:
    output = await use_case.execute(ListCategoriesInputDTO(user_id=user_id))
    return CategoriesListResponse(**output.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CategoryResponse)
async def create_category(
    body: CreateCategoryRequest,
    user_id: UUID = Depends(get_current_user_id),
    tier: str = Depends(get_current_tier),
    use_case: CreateCategoryUseCase = Depends(_depends_create_use_case),
) -> CategoryResponse:
    output = await use_case.execute(
        CreateCategoryInputDTO(
            user_id=user_id,
            tier=tier,
            name=body.name,
            icon=body.icon,
            color=body.color,
            flow=body.flow,
        )
    )
    return CategoryResponse(**output.model_dump())


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    body: UpdateCategoryRequest,
    user_id: UUID = Depends(get_current_user_id),
    use_case: UpdateCategoryUseCase = Depends(_depends_update_use_case),
) -> CategoryResponse:
    output = await use_case.execute(
        UpdateCategoryInputDTO(
            user_id=user_id,
            category_id=category_id,
            name=body.name,
            icon=body.icon,
            color=body.color,
        )
    )
    return CategoryResponse(**output.model_dump())


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    user_id: UUID = Depends(get_current_user_id),
    use_case: DeleteCategoryUseCase = Depends(_depends_delete_use_case),
) -> None:
    await use_case.execute(DeleteCategoryInputDTO(user_id=user_id, category_id=category_id))
