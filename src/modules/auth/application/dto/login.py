from pydantic import BaseModel


class LoginInputDTO(BaseModel):
    email: str
    password: str
