from datetime import datetime

from pydantic import BaseModel

from core.datastore.model import TransactionDirection


class AppleAccountInfo(BaseModel):
    id: str
    display_name: str
    available_balance: float | None = None
    institution_name: str | None = None
    card_last4: str | None = None


class AppleTransaction(BaseModel):
    id: str
    account_id: str
    name: str
    amount: float
    direction: TransactionDirection
    date: datetime


class AppleAccountTransactions(BaseModel):
    account: AppleAccountInfo
    transactions: list[AppleTransaction]
