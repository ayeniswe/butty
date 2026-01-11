from abc import ABC, abstractmethod
from datetime import datetime

from .model import (
    Account,
    Budget,
    PartialAccount,
    PartialBudget,
    PartialTransaction,
    PlaidAccount,
    Tag,
    Transaction,
    TransactionView,
)


class DataStore(ABC):
    # -------- Budgets --------
    @abstractmethod
    def update_budget(self, obj: PartialBudget): ...

    @abstractmethod
    def insert_budget(
        self,
        name: str,
        amount_allocated: float,
        override_create_date: datetime | None = None,
    ): ...

    @abstractmethod
    def delete_budget(self, id: int): ...

    @abstractmethod
    def select_budget(self, id: int) -> Budget: ...

    @abstractmethod
    def filter_budgets(self, start: datetime, end: datetime) -> list[Budget]: ...

    @abstractmethod
    def retrieve_budgets(self) -> list[Budget]: ...

    # -------- Transactions --------
    @abstractmethod
    def update_transaction_note(self, id: int, note: str): ...

    @abstractmethod
    def insert_transaction(self, obj: PartialTransaction) -> int | None: ...

    @abstractmethod
    def delete_transaction(self, id: int): ...

    @abstractmethod
    def select_transaction(self, id: int) -> Transaction: ...

    @abstractmethod
    def select_transaction_id_by_fingerprint_or_external_id(
        self, fingerprint: str, external_id: str | None
    ) -> int | None: ...

    @abstractmethod
    def retrieve_transactions(self) -> list[TransactionView]: ...

    @abstractmethod
    def filter_transactions(
        self, start: datetime, end: datetime
    ) -> list[TransactionView]: ...

    # -------- Tags --------
    @abstractmethod
    def update_tag(self, obj: Tag): ...

    @abstractmethod
    def insert_tag(self, name: str) -> int: ...

    @abstractmethod
    def delete_tag(self, id: int): ...

    @abstractmethod
    def select_tag(self, id: int) -> Tag: ...

    @abstractmethod
    def retrieve_tags(self) -> list[Tag]: ...

    # -------- Budget ↔ Tags --------
    @abstractmethod
    def insert_budget_tag(self, budget_id: int, tag_id: int): ...

    @abstractmethod
    def delete_budget_tag(self, budget_id: int, tag_id: int): ...

    @abstractmethod
    def retrieve_budget_tags(self, budget_id: int) -> list[Tag]: ...

    # -------- Plaid Accounts --------
    @abstractmethod
    def insert_plaid_account(self, token: str) -> int: ...

    @abstractmethod
    def delete_plaid_account(self, id: int): ...

    @abstractmethod
    def select_plaid_account(self, id: int) -> PlaidAccount: ...

    @abstractmethod
    def retrieve_plaid_accounts(self) -> list[PlaidAccount]: ...

    # -------- Accounts --------
    @abstractmethod
    def account_exists_by_fingerprint(self, fingerprint: str) -> int | None: ...

    @abstractmethod
    def insert_account(self, obj: PartialAccount) -> int: ...

    @abstractmethod
    def delete_account(self, id: int): ...

    @abstractmethod
    def select_account(self, id: int) -> Account: ...

    @abstractmethod
    def select_account_by_id(self, id: int) -> Account: ...

    @abstractmethod
    def retrieve_accounts(self) -> list[Account]: ...

    # -------- Budget ↔ Transactions --------
    @abstractmethod
    def insert_budget_transaction(self, budget_id: int, transaction_id: int): ...

    @abstractmethod
    def delete_budget_transaction(self, budget_id: int, transaction_id: int): ...

    @abstractmethod
    def retrieve_budget_transactions(self, budget_id: int) -> list[TransactionView]: ...

    @abstractmethod
    def select_budget_id_for_transaction(self, transaction_id: int) -> int | None: ...
