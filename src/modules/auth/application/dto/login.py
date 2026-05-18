from pydantic import BaseModel


class LoginInputDTO(BaseModel):
    email: str
    password: str


class LoginOutputDTO(BaseModel):
    user_id: str
    email: str
    display_name: str
    tier: str
    access_token: str
