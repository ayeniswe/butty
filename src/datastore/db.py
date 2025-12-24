from pathlib import Path
from typing import List
from sqlalchemy import MetaData, create_engine, delete, update, insert, select
from .model import Budget, PartialTransaction, Tag, Transaction


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

        self.meta = MetaData()
        self.meta.reflect(bind=self.engine)
        self.budgets = self.meta.tables["budgets"]
        self.tags = self.meta.tables["tags"]
        self.budgets_tags = self.meta.tables["budgets_tags"]
        self.transactions = self.meta.tables["transactions"]

    def update_budget(self, obj: Budget):
        with self.engine.begin() as conn:
            conn.execute(
                update(self.budgets).values(
                    name=obj.name,
                    amount_allocated=obj.amount_allocated,
                    amount_spent=obj.amount_spent,
                    level=obj.level).where(self.budgets.c.id == obj.id))

    def insert_budget(self, name: str, amount_allocated: float = 0.0):
        with self.engine.begin() as conn:
            conn.execute(
                insert(self.budgets).values(name=name,
                                            amount_allocated=amount_allocated))

    def delete_budget(self, id: int):
        with self.engine.begin() as conn:
            conn.execute(delete(self.budgets).where(self.budgets.c.id == id))

    def select_budget(self, id: int) -> Budget:
        with self.engine.begin() as conn:
            return conn.execute(
                select(
                    self.budgets).where(self.budgets.c.id == id)).fetchone()

    def get_budgets(self) -> List[Budget]:
        with self.engine.begin() as conn:
            return conn.execute(select(self.budgets)).fetchall()

    def update_transaction_note(self, id: int, note: str):
        with self.engine.begin() as conn:
            conn.execute(
                update(self.transactions).values(note=note).where(
                    self.transactions.c.id == id))

    def insert_transaction(self, obj: PartialTransaction):
        with self.engine.begin() as conn:
            values = {
                "name": obj.name,
                "amount": obj.amount,
                "direction": obj.direction,
                "note": obj.note,
            }
            if obj.occurred_at:
                values["occurred_at"] = obj.occurred_at
            conn.execute(insert(self.transactions).values(values))

    def delete_transaction(self, id: int):
        with self.engine.begin() as conn:
            conn.execute(
                delete(self.transactions).where(self.transactions.c.id == id))

    def select_transaction(self, id: int) -> Transaction:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.transactions).where(
                    self.transactions.c.id == id)).fetchone()

    def get_transactions(self) -> List[Transaction]:
        with self.engine.begin() as conn:
            return conn.execute(select(self.transactions)).fetchall()

    def update_tag(self, obj: Tag):
        with self.engine.begin() as conn:
            conn.execute(
                update(self.tags).values(name=obj.name).where(
                    self.tags.c.id == obj.id))

    def insert_tag(self, name: str):
        with self.engine.begin() as conn:
            conn.execute(insert(self.tags).values(name=name))

    def delete_tag(self, id: int):
        with self.engine.begin() as conn:
            conn.execute(delete(self.tags).where(self.tags.c.id == id))

    def select_tag(self, id: int) -> Tag:
        with self.engine.begin() as conn:
            return conn.execute(select(
                self.tags).where(self.tags.c.id == id)).fetchone()

    def get_tags(self) -> Tag:
        with self.engine.begin() as conn:
            return conn.execute(select(self.tags)).fetchall()

    def tag_budget(self, budget_id: int, tag_id: int):
        with self.engine.begin() as conn:
            conn.execute(
                insert(self.budgets_tags).values(tag_id=tag_id,
                                                 budget_id=budget_id))

    def untag_budget(self, budget_id: int, tag_id: int):
        with self.engine.begin() as conn:
            conn.execute(
                delete(self.budgets_tags).where(
                    self.budgets_tags.c.tag_id == tag_id
                    and self.budgets_tags.c.budget_id == budget_id))
