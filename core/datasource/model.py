from dataclasses import dataclass


@dataclass(frozen=True)
class PlaidAccountBase:
    account_id: int
    name: str
    fingerprint: str
    type: str
    balance: float


@dataclass(frozen=True)
class PlaidTransactionSync:
    added: list
    modified: list
    removed_ids: list[str]
    next_cursor: str | None
