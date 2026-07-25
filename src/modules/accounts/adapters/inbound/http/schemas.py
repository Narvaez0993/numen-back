from pydantic import BaseModel, Field

# Money fields are integers in the minor unit of the user's currency.


class AccountResponse(BaseModel):
    id: str
    kind: str
    name: str
    sub: str
    icon: str
    color: str
    currency: str
    balance: int


class CreditCardResponse(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    currency: str
    debt: int
    limit: int
    cutoff_day: int
    due_day: int | None


class AccountsOverviewResponse(BaseModel):
    currency: str
    accounts: list[AccountResponse]
    credit_cards: list[CreditCardResponse]
    debit_total: int
    cash_total: int
    tc_debt: int
    net_balance: int
    accounts_count: int
    credit_cards_count: int


class CreateAccountRequest(BaseModel):
    kind: str
    name: str = Field(min_length=1, max_length=40)
    sub: str = Field(default="", max_length=40)
    icon: str = Field(default="", max_length=40)
    color: str = Field(default="", max_length=20)
    balance: int = 0


class UpdateAccountRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    sub: str | None = Field(default=None, max_length=40)
    icon: str | None = Field(default=None, min_length=1, max_length=40)
    color: str | None = Field(default=None, max_length=20)
    balance: int | None = None


class CreateCreditCardRequest(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    icon: str = Field(default="", max_length=40)
    color: str = Field(default="", max_length=20)
    debt: int = 0
    limit: int
    cutoff_day: int
    due_day: int | None = None


class UpdateCreditCardRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    icon: str | None = Field(default=None, min_length=1, max_length=40)
    color: str | None = Field(default=None, max_length=20)
    debt: int | None = None
    limit: int | None = None
    cutoff_day: int | None = None
    due_day: int | None = None
