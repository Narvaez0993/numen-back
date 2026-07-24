from pydantic import BaseModel


class RefreshInputDTO(BaseModel):
    refresh_token: str


class LogoutInputDTO(BaseModel):
    refresh_token: str
