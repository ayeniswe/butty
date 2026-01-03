from dataclasses import dataclass


@dataclass(frozen=True)
class PlaidAccountBase:
    account_id: int
    name: str
    fingerprint: str
    type: str
    balance: float
