from pydantic import BaseModel


class ResendCodeInputDTO(BaseModel):
    email: str
