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


@dataclass(frozen=True)
class Transaction:
    id: int
    name: str
    amount: int
    direction: TransactionDirection
    occurred_at: datetime
    note: str | None


@dataclass(frozen=True)
class PartialTransaction:
    name: str
    amount: int
    direction: TransactionDirection
    note: str | None = None
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
