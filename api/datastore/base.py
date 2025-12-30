from abc import ABC, abstractmethod
from datetime import datetime

from .model import (
    Account,
    Budget,
    PartialAccount,
    PartialTransaction,
    PlaidAccount,
    Tag,
    Transaction,
)


class DataStore(ABC):
    # -------- Budgets --------
    @abstractmethod
    def update_budget(self, obj: Budget): ...

    @abstractmethod
    def insert_budget(self, name: str, amount_allocated: float = 0.0): ...

    @abstractmethod
    def delete_budget(self, id: int): ...

    @abstractmethod
    def select_budget(self, id: int) -> Budget: ...

    @abstractmethod
    def filter_budgets(self, start: datetime, end: datetime) -> list[Budget]: ...

    @abstractmethod
    def get_budgets(self) -> list[Budget]: ...

    # -------- Transactions --------
    @abstractmethod
    def update_transaction_note(self, id: int, note: str): ...

    @abstractmethod
    def insert_transaction(self, obj: PartialTransaction): ...

    @abstractmethod
    def delete_transaction(self, id: int): ...

    @abstractmethod
    def select_transaction(self, id: int) -> Transaction: ...

    @abstractmethod
    def get_transactions(self) -> list[Transaction]: ...

    @abstractmethod
    def filter_transactions(
        self, start: datetime, end: datetime
    ) -> list[Transaction]: ...

    # -------- Tags --------
    @abstractmethod
    def update_tag(self, obj: Tag): ...

    @abstractmethod
    def insert_tag(self, name: str): ...

    @abstractmethod
    def delete_tag(self, id: int): ...

    @abstractmethod
    def select_tag(self, id: int) -> Tag: ...

    @abstractmethod
    def get_tags(self) -> list[Tag]: ...

    # -------- Budget ↔ Tags --------
    @abstractmethod
    def tag_budget(self, budget_id: int, tag_id: int): ...

    @abstractmethod
    def untag_budget(self, budget_id: int, tag_id: int): ...

    # -------- Plaid Accounts --------
    @abstractmethod
    def insert_plaid_account(self, token: str) -> int: ...

    @abstractmethod
    def delete_plaid_account(self, id: int): ...

    @abstractmethod
    def select_plaid_account(self, id: int) -> PlaidAccount: ...

    @abstractmethod
    def get_plaid_accounts(self) -> list[PlaidAccount]: ...

    # -------- Accounts --------
    @abstractmethod
    def insert_account(self, obj: PartialAccount) -> int: ...

    @abstractmethod
    def delete_account(self, id: int): ...

    @abstractmethod
    def select_account(self, id: int) -> Account: ...

    @abstractmethod
    def select_account_by_ext_id(self, id: int) -> Account: ...

    @abstractmethod
    def get_accounts(self) -> list[Account]: ...

    # -------- Budget ↔ Transactions --------
    @abstractmethod
    def add_budget_transaction(self, budget_id: int, transaction_id: int): ...

    @abstractmethod
    def delete_budget_transaction(self, budget_id: int, transaction_id: int): ...
