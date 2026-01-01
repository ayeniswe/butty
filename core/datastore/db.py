# MARK: Imports
from datetime import datetime
from pathlib import Path

from sqlalchemy import MetaData, create_engine, delete, insert, select, update

from core.datastore.base import DataStore
from core.datastore.model import (
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
from core.utils import dollars_to_cents


# MARK: SQLite Datastore
class Sqlite3(DataStore):
    def __init__(self, db_path: Path):
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)

        with self.engine.begin() as conn:
            import sqlite3

            conn: sqlite3.Connection = conn.connection.driver_connection
            conn.executescript(open("schema/tags.sql").read())
            conn.executescript(open("schema/budgets.sql").read())
            conn.executescript(open("schema/budgets_tags.sql").read())
            conn.executescript(open("schema/transactions.sql").read())
            conn.executescript(open("schema/plaid_accounts.sql").read())
            conn.executescript(open("schema/accounts.sql").read())
            conn.executescript(open("schema/budgets_transactions.sql").read())

        self.meta = MetaData()
        self.meta.reflect(bind=self.engine)
        self.budgets = self.meta.tables["budgets"]
        self.tags = self.meta.tables["tags"]
        self.budgets_tags = self.meta.tables["budgets_tags"]
        self.budgets_transactions = self.meta.tables["budgets_transactions"]
        self.transactions = self.meta.tables["transactions"]
        self.plaid_accounts = self.meta.tables["plaid_accounts"]
        self.accounts = self.meta.tables["accounts"]

    # MARK: - Budgets
    def insert_budget(
        self,
        name: str,
        amount_allocated: float,
        override_create_date: datetime | None = None,
    ):
        with self.engine.begin() as conn:
            values = {
                "name": name,
                "amount_allocated": dollars_to_cents(amount_allocated),
            }
            if override_create_date:
                values["created_at"] = override_create_date.isoformat()
            conn.execute(insert(self.budgets).values(values))

    def update_budget(self, obj: PartialBudget):
        with self.engine.begin() as conn:
            conn.execute(
                update(self.budgets)
                .values(
                    name=obj.name,
                    amount_allocated=dollars_to_cents(
                        obj.amount_allocated
                    ),  # Can be effected by user input since they will pass as dollars
                    amount_spent=obj.amount_spent,  # Should be managed internally only since it's calculated from transactions
                    level=obj.level,
                )
                .where(self.budgets.c.id == obj.id)
            )

    def delete_budget(self, id: int):
        with self.engine.begin() as conn:
            conn.execute(delete(self.budgets).where(self.budgets.c.id == id))

    def select_budget(self, id: int) -> Budget:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.budgets).where(self.budgets.c.id == id)
            ).fetchone()

    def retrieve_budgets(self) -> list[Budget]:
        with self.engine.begin() as conn:
            return conn.execute(select(self.budgets)).fetchall()

    def filter_budgets(self, start: datetime, end: datetime) -> list[Budget]:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.budgets)
                .where(self.budgets.c.created_at >= start.date())
                .where(self.budgets.c.created_at < end.date())
            ).fetchall()

    # MARK: - Transactions
    def insert_transaction(self, obj: PartialTransaction) -> int:
        with self.engine.begin() as conn:
            values = {
                "name": obj.name,
                "amount": dollars_to_cents(obj.amount),
                "direction": obj.direction,
                "external_id": obj.external_id,
                "account_id": obj.account_id,
            }
            if obj.occurred_at:
                values["occurred_at"] = obj.occurred_at.isoformat()
            if obj.note:
                values["note"] = obj.note
            result = conn.execute(
                insert(self.transactions).values(values).prefix_with("OR IGNORE")
            )
            return result.inserted_primary_key[0]

    def update_transaction_note(self, id: int, note: str):
        with self.engine.begin() as conn:
            conn.execute(
                update(self.transactions)
                .values(note=note)
                .where(self.transactions.c.id == id)
            )

    def delete_transaction(self, id: int):
        with self.engine.begin() as conn:
            conn.execute(delete(self.transactions).where(self.transactions.c.id == id))

    def select_transaction(self, id: int) -> Transaction:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.transactions).where(self.transactions.c.id == id)
            ).fetchone()

    def retrieve_transactions(self) -> list[TransactionView]:
        with self.engine.begin() as conn:
            return conn.execute(
                select(
                    self.transactions,
                    self.accounts.c.name.label("account_name"),
                    self.budgets.c.name.label("budget_name"),
                )
                .join(
                    self.budgets_transactions,
                    self.transactions.c.id
                    == self.budgets_transactions.c.transaction_id,
                )
                .join(
                    self.budgets,
                    self.budgets_transactions.c.budget_id == self.budgets.c.id,
                )
                .join(
                    self.accounts, self.transactions.c.account_id == self.accounts.c.id
                )
            ).fetchall()

    def filter_transactions(
        self, start: datetime, end: datetime
    ) -> list[TransactionView]:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.transactions, self.accounts.c.name.label("account_name"))
                .join(
                    self.accounts, self.transactions.c.account_id == self.accounts.c.id
                )
                .where(self.transactions.c.occurred_at >= start.date())
                .where(self.transactions.c.occurred_at < end.date())
                .order_by(self.transactions.c.occurred_at.desc())
            ).fetchall()

    # MARK: - Tags
    def insert_tag(self, name: str) -> int:
        with self.engine.begin() as conn:
            result = conn.execute(insert(self.tags).values(name=name))
            return result.inserted_primary_key[0]

    def update_tag(self, obj: Tag):
        with self.engine.begin() as conn:
            conn.execute(
                update(self.tags).values(name=obj.name).where(self.tags.c.id == obj.id)
            )

    def delete_tag(self, id: int):
        with self.engine.begin() as conn:
            conn.execute(delete(self.tags).where(self.tags.c.id == id))

    def select_tag(self, id: int) -> Tag:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.tags).where(self.tags.c.id == id)
            ).fetchone()

    def retrieve_tags(self) -> Tag:
        with self.engine.begin() as conn:
            return conn.execute(select(self.tags)).fetchall()

    # MARK: - Budget ↔ Tag Links
    def insert_budget_tag(self, budget_id: int, tag_id: int):
        with self.engine.begin() as conn:
            conn.execute(
                insert(self.budgets_tags)
                .values(tag_id=tag_id, budget_id=budget_id)
                .prefix_with("OR IGNORE")
            )

    def delete_budget_tag(self, budget_id: int, tag_id: int):
        with self.engine.begin() as conn:
            conn.execute(
                delete(self.budgets_tags)
                .where(self.budgets_tags.c.tag_id == tag_id)
                .where(self.budgets_tags.c.budget_id == budget_id)
            )

    def retrieve_budget_tags(self, id: int) -> list[Tag]:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.tags)
                .join(
                    self.budgets_tags,
                    self.tags.c.id == self.budgets_tags.c.tag_id,
                )
                .where(self.budgets_tags.c.budget_id == id)
            ).fetchall()

    # MARK: - Plaid Accounts
    def insert_plaid_account(self, token: str) -> int:
        with self.engine.begin() as conn:
            result = conn.execute(insert(self.plaid_accounts).values(token=token))
            return result.inserted_primary_key[0]

    def delete_plaid_account(self, id: int):
        with self.engine.begin() as conn:
            conn.execute(
                delete(self.plaid_accounts).where(self.plaid_accounts.c.id == id)
            )

    def select_plaid_account(self, id: int) -> PlaidAccount:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.plaid_accounts).where(self.plaid_accounts.c.id == id)
            ).fetchone()

    def retrieve_plaid_accounts(self) -> list[PlaidAccount]:
        with self.engine.begin() as conn:
            return conn.execute(select(self.plaid_accounts)).fetchall()

    # MARK: - Accounts
    def insert_account(self, obj: PartialAccount) -> int:
        values = {
            "name": obj.name,
            "external_id": obj.external_id,
            "source": obj.source,
            "account_type": obj.account_type,
            "balance": obj.balance,
        }
        if obj.plaid_id:
            values["plaid_id"] = obj.plaid_id
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(self.accounts).values(values).prefix_with("OR IGNORE")
            )
            return result.inserted_primary_key[0]

    def delete_account(self, id: int):
        with self.engine.begin() as conn:
            conn.execute(delete(self.accounts).where(self.accounts.c.id == id))

    def select_account(self, id: int) -> Account:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.accounts).where(self.accounts.c.id == id)
            ).fetchone()

    def select_account_by_id(self, id: int) -> Account:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.accounts).where(self.accounts.c.id == id)
            ).first()

    def select_account_by_ext_id(self, id: int) -> Account:
        # Could class with duplicaties on re-link
        # so we only care about first since
        # data we care about should be identical
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.accounts).where(self.accounts.c.external_id == id)
            ).first()

    def retrieve_accounts(self) -> list[Account]:
        with self.engine.begin() as conn:
            return conn.execute(select(self.accounts)).fetchall()

    # MARK: - Budget ↔ Transaction Links / Views
    def insert_budget_transaction(self, budget_id: int, transaction_id: int):
        with self.engine.begin() as conn:
            conn.execute(
                insert(self.budgets_transactions).values(
                    transaction_id=transaction_id, budget_id=budget_id
                )
            )

    def delete_budget_transaction(self, budget_id: int, transaction_id: int):
        with self.engine.begin() as conn:
            conn.execute(
                delete(self.budgets_transactions)
                .where(self.budgets_transactions.c.transaction_id == transaction_id)
                .where(self.budgets_transactions.c.budget_id == budget_id)
            )

    def retrieve_budget_transactions(self, budget_id: int) -> list[TransactionView]:
        """
        Return all transactions linked to a given budget.
        """
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.transactions, self.accounts.c.name.label("account_name"))
                .join(
                    self.budgets_transactions,
                    self.transactions.c.id
                    == self.budgets_transactions.c.transaction_id,
                )
                .join(
                    self.accounts, self.transactions.c.account_id == self.accounts.c.id
                )
                .where(self.budgets_transactions.c.budget_id == budget_id)
                .order_by(self.transactions.c.occurred_at.desc())
            ).fetchall()
