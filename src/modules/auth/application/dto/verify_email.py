from pydantic import BaseModel


class VerifyEmailInputDTO(BaseModel):
    email: str
    code: str
