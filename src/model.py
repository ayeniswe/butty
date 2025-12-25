from datetime import datetime

from datastore.model import TransactionDirection
from pydantic import BaseModel


class PlaidExchangeRequest(BaseModel):
    public_token: str


class AppleTransaction(BaseModel):
    id: str
    account_id: str
    name: str
    amount: float
    direction: TransactionDirection
    date: datetime
