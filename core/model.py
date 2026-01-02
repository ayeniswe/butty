from datetime import datetime

from pydantic import BaseModel

from core.datastore.model import TransactionDirection


class AppleTransaction(BaseModel):
    id: str
    account_id: str
    name: str
    amount: float
    direction: TransactionDirection
    date: datetime
