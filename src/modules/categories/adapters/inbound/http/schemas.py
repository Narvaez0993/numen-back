from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    flow: str
    is_standard: bool


class CategoriesListResponse(BaseModel):
    categories: list[CategoryResponse]


class CreateCategoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    icon: str = Field(min_length=1, max_length=40)
    color: str
    flow: str


class UpdateCategoryRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    icon: str | None = Field(default=None, min_length=1, max_length=40)
    color: str | None = None
