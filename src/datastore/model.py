from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class BudgetLevel(StrEnum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class TransactionDirection(StrEnum):
    IN = "IN"
    OUT = "OUT"

class TransactionSource(StrEnum):
    PLAID = "PLAID"
    APPLE = "APPLE"

class TransactionType(StrEnum):
    CREDIT = "CREDIT"
    DEPOSITORY = "DEPOSITORY"
    LOAN = "LOAN"
    INVESTMENT = "INVESTMENT"


@dataclass(frozen=True)
class Transaction:
    id: int
    name: str
    amount: int
    direction: TransactionDirection
    occurred_at: datetime
    account_id: int
    external_id: str | None
    note: str | None


@dataclass(frozen=True)
class PartialTransaction:
    name: str
    amount: int
    direction: TransactionDirection
    account_id: int 
    note: str | None = None
    external_id: str | None = None
    occurred_at: datetime | None = None


@dataclass(frozen=True)
class Budget:
    id: int
    name: str
    amount_allocated: float
    amount_spent: float
    amount_saved: float
    level: BudgetLevel | None = None


@dataclass(frozen=True)
class Tag:
    id: int
    name: str

@dataclass(frozen=True)
class PlaidAccount:
    id: int
    token: str

@dataclass(frozen=True)
class Account:
    id: int
    external_id: str
    account_type: str
    source: TransactionSource
    name: str
    plaid_id: int | None

@dataclass(frozen=True)
class PartialAccount:
    external_id: str
    source: TransactionSource
    account_type: str
    name: str
    plaid_id: int | None = None
