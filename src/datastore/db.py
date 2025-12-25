from datetime import datetime
from pathlib import Path

from sqlalchemy import MetaData, create_engine, delete, insert, select, update

from .model import (
    Account,
    Budget,
    PartialAccount,
    PartialTransaction,
    PlaidAccount,
    Tag,
    Transaction,
)


class Sqlite3:
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

    def update_budget(self, obj: Budget):
        with self.engine.begin() as conn:
            conn.execute(
                update(self.budgets)
                .values(
                    name=obj.name,
                    amount_allocated=obj.amount_allocated,
                    amount_spent=obj.amount_spent,
                    level=obj.level,
                )
                .where(self.budgets.c.id == obj.id)
            )

    def insert_budget(self, name: str, amount_allocated: float = 0.0):
        with self.engine.begin() as conn:
            conn.execute(
                insert(self.budgets).values(
                    name=name, amount_allocated=amount_allocated
                )
            )

    def delete_budget(self, id: int):
        with self.engine.begin() as conn:
            conn.execute(delete(self.budgets).where(self.budgets.c.id == id))

    def select_budget(self, id: int) -> Budget:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.budgets).where(self.budgets.c.id == id)
            ).fetchone()

    def filter_budgets(self, start: datetime, end: datetime) -> list[Budget]:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.budgets)
                .where(self.budgets.c.created_at >= start)
                .where(self.budgets.c.created_at < end)
            ).fetchall()

    def get_budgets(self) -> list[Budget]:
        with self.engine.begin() as conn:
            return conn.execute(select(self.budgets)).fetchall()

    def update_transaction_note(self, id: int, note: str):
        with self.engine.begin() as conn:
            conn.execute(
                update(self.transactions)
                .values(note=note)
                .where(self.transactions.c.id == id)
            )

    def insert_transaction(self, obj: PartialTransaction):
        with self.engine.begin() as conn:
            values = {
                "name": obj.name,
                "amount": obj.amount,
                "direction": obj.direction,
                "note": obj.note,
                "external_id": obj.external_id,
                "account_id": obj.account_id,
            }
            if obj.occurred_at:
                values["occurred_at"] = obj.occurred_at
            conn.execute(
                insert(self.transactions).values(values).prefix_with("OR IGNORE")
            )

    def delete_transaction(self, id: int):
        with self.engine.begin() as conn:
            conn.execute(delete(self.transactions).where(self.transactions.c.id == id))

    def select_transaction(self, id: int) -> Transaction:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.transactions).where(self.transactions.c.id == id)
            ).fetchone()

    def get_transactions(self) -> list[Transaction]:
        with self.engine.begin() as conn:
            return conn.execute(select(self.transactions)).fetchall()

    def filter_transactions(self, start: datetime, end: datetime) -> list[Transaction]:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.transactions)
                .where(self.transactions.c.occurred_at >= start)
                .where(self.transactions.c.occurred_at < end)
            ).fetchall()

    def update_tag(self, obj: Tag):
        with self.engine.begin() as conn:
            conn.execute(
                update(self.tags).values(name=obj.name).where(self.tags.c.id == obj.id)
            )

    def insert_tag(self, name: str):
        with self.engine.begin() as conn:
            conn.execute(insert(self.tags).values(name=name))

    def delete_tag(self, id: int):
        with self.engine.begin() as conn:
            conn.execute(delete(self.tags).where(self.tags.c.id == id))

    def select_tag(self, id: int) -> Tag:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.tags).where(self.tags.c.id == id)
            ).fetchone()

    def get_tags(self) -> Tag:
        with self.engine.begin() as conn:
            return conn.execute(select(self.tags)).fetchall()

    def tag_budget(self, budget_id: int, tag_id: int):
        with self.engine.begin() as conn:
            conn.execute(
                insert(self.budgets_tags).values(tag_id=tag_id, budget_id=budget_id)
            )

    def untag_budget(self, budget_id: int, tag_id: int):
        with self.engine.begin() as conn:
            conn.execute(
                delete(self.budgets_tags)
                .where(self.budgets_tags.c.tag_id == tag_id)
                .where(self.budgets_tags.c.budget_id == budget_id)
            )

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

    def get_plaid_accounts(self) -> list[PlaidAccount]:
        with self.engine.begin() as conn:
            return conn.execute(select(self.plaid_accounts)).fetchall()

    def insert_account(self, obj: PartialAccount) -> int:
        values = {
            "name": obj.name,
            "external_id": obj.external_id,
            "source": obj.source,
            "account_type": obj.account_type,
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

    def select_account_by_ext_id(self, id: int) -> Account:
        # Could class with duplicaties on re-link
        # so we only care about first since
        # data we care about should be identical
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.accounts).where(self.accounts.c.external_id == id)
            ).first()

    def get_accounts(self) -> list[Account]:
        with self.engine.begin() as conn:
            return conn.execute(select(self.accounts)).fetchall()

    def add_budget_transaction(self, budget_id: int, transaction_id: int):
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
