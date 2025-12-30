from datetime import datetime

from pydantic import BaseModel

from api.datastore.model import TransactionDirection


class PlaidExchangeRequest(BaseModel):
    public_token: str


class AppleTransaction(BaseModel):
    id: str
    account_id: str
    name: str
    amount: float
    direction: TransactionDirection
    date: datetime
