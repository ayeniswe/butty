# MARK: Imports
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, create_engine, delete, insert, or_, select, update

from core.datastore.base import DataStore
from core.datastore.model import (
    Account,
    Budget,
    PartialAccount,
    PartialBudget,
    PartialTransaction,
    PlaidAccount,
    PlaidCategory,
    PlaidCategoryMapping,
    Tag,
    Transaction,
    TransactionView,
)
from core.utils import dollars_to_cents

# MARK: SQLite Datastore
SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "schema"


def _load_sql(name: str) -> str:
    return (SCHEMA_DIR / name).read_text()


class Sqlite3(DataStore):
    def __init__(self, db_path: Path):
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)

        with self.engine.begin() as conn:
            import sqlite3

            conn: sqlite3.Connection = conn.connection.driver_connection
            conn.executescript(_load_sql("tags.sql"))
            conn.executescript(_load_sql("budgets.sql"))
            conn.executescript(_load_sql("budgets_tags.sql"))
            conn.executescript(_load_sql("plaid_categories.sql"))
            conn.executescript(_load_sql("transactions.sql"))
            conn.executescript(_load_sql("plaid_accounts.sql"))
            conn.executescript(_load_sql("accounts.sql"))
            conn.executescript(_load_sql("plaid_category_mappings.sql"))
            conn.executescript(_load_sql("budgets_transactions.sql"))
            self.__apply_migrations(conn)

        self.meta = MetaData()
        self.meta.reflect(bind=self.engine)
        self.budgets = self.meta.tables["budgets"]
        self.tags = self.meta.tables["tags"]
        self.budgets_tags = self.meta.tables["budgets_tags"]
        self.budgets_transactions = self.meta.tables["budgets_transactions"]
        self.transactions = self.meta.tables["transactions"]
        self.plaid_accounts = self.meta.tables["plaid_accounts"]
        self.accounts = self.meta.tables["accounts"]
        self.plaid_categories = self.meta.tables["plaid_categories"]
        self.plaid_category_mappings = self.meta.tables["plaid_category_mappings"]

    @staticmethod
    def __apply_migrations(conn):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        migrations_dir = SCHEMA_DIR / "migrations"
        if not migrations_dir.is_dir():
            return

        migration_guards = {
            "001_add_plaid_cursor.sql": lambda c: "cursor"
            not in {row[1] for row in c.execute("PRAGMA table_info(plaid_accounts)")},
            "002_add_plaid_category_to_transactions.sql": lambda c: "plaid_category_id"
            not in {row[1] for row in c.execute("PRAGMA table_info(transactions)")},
            "003_add_institution_to_plaid_accounts.sql": lambda c: "institution_id"
            not in {row[1] for row in c.execute("PRAGMA table_info(plaid_accounts)")},
        }

        for path in sorted(migrations_dir.glob("*.sql")):
            name = path.name
            already_applied = conn.execute(
                "SELECT 1 FROM migrations WHERE name = ?", (name,)
            ).fetchone()
            if already_applied:
                continue

            guard = migration_guards.get(name)
            if guard and not guard(conn):
                conn.execute("INSERT INTO migrations (name) VALUES (?)", (name,))
                continue

            conn.executescript(path.read_text())
            conn.execute("INSERT INTO migrations (name) VALUES (?)", (name,))

    @staticmethod
    def __rows_to_transaction_views(rows: Any) -> list[TransactionView]:
        views = []
        for row in rows:
            data = dict(row._mapping)
            occurred = data.get("occurred_at")
            data.pop("account_id")
            data.pop("fingerprint")
            if isinstance(occurred, str):
                data["occurred_at"] = datetime.fromisoformat(occurred)
            views.append(TransactionView(**data))
        return views

    # MARK: - Budgets
    def insert_budget(
        self,
        name: str,
        amount_allocated: float,
        override_create_date: datetime | None = None,
    ) -> int:
        with self.engine.begin() as conn:
            values = {
                "name": name,
                "amount_allocated": dollars_to_cents(amount_allocated),
            }
            if override_create_date:
                values["created_at"] = override_create_date.isoformat()
            result = conn.execute(insert(self.budgets).values(values))
            return result.inserted_primary_key[0]

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
            conn.execute(
                delete(self.plaid_category_mappings).where(
                    self.plaid_category_mappings.c.budget_id == id
                )
            )
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
    def insert_transaction(self, obj: PartialTransaction) -> int | None:
        with self.engine.begin() as conn:
            values = {
                "name": obj.name,
                "amount": dollars_to_cents(obj.amount),
                "direction": obj.direction,
                "external_id": obj.external_id,
                "account_id": obj.account_id,
                "fingerprint": obj.fingerprint,
            }
            if obj.occurred_at:
                values["occurred_at"] = obj.occurred_at.isoformat()
            if obj.note:
                values["note"] = obj.note
            if obj.plaid_category_id:
                values["plaid_category_id"] = obj.plaid_category_id
            result = conn.execute(
                insert(self.transactions).values(values).prefix_with("OR IGNORE")
            )
            if result.rowcount == 0:
                return None
            return result.inserted_primary_key[0]

    def update_transaction_note(self, id: int, note: str):
        with self.engine.begin() as conn:
            conn.execute(
                update(self.transactions)
                .values(note=note)
                .where(self.transactions.c.id == id)
            )

    def update_transaction_plaid_category(self, id: int, plaid_category_id: int):
        with self.engine.begin() as conn:
            conn.execute(
                update(self.transactions)
                .values(plaid_category_id=plaid_category_id)
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

    def select_transaction_id_by_fingerprint_or_external_id(
        self, fingerprint: str, external_id: str | None
    ) -> int | None:
        with self.engine.begin() as conn:
            if external_id:
                condition = or_(
                    self.transactions.c.fingerprint == fingerprint,
                    self.transactions.c.external_id == external_id,
                )
            else:
                condition = self.transactions.c.fingerprint == fingerprint
            row = conn.execute(
                select(self.transactions.c.id).where(condition)
            ).fetchone()
            return row[0] if row else None

    def retrieve_transactions(self) -> list[TransactionView]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(
                    self.transactions,
                    self.accounts.c.name.label("account_name"),
                    self.budgets.c.name.label("budget_name"),
                )
                .join(
                    self.accounts, self.transactions.c.account_id == self.accounts.c.id
                )
                .outerjoin(
                    self.budgets_transactions,
                    self.transactions.c.id
                    == self.budgets_transactions.c.transaction_id,
                )
                .outerjoin(
                    self.budgets,
                    self.budgets_transactions.c.budget_id == self.budgets.c.id,
                )
                .order_by(self.transactions.c.occurred_at.desc())
            ).fetchall()

            return Sqlite3.__rows_to_transaction_views(rows)

    def filter_transactions(
        self, start: datetime, end: datetime
    ) -> list[TransactionView]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(
                    self.transactions,
                    self.accounts.c.name.label("account_name"),
                    self.budgets.c.name.label("budget_name"),
                )
                .join(
                    self.accounts, self.transactions.c.account_id == self.accounts.c.id
                )
                .outerjoin(
                    self.budgets_transactions,
                    self.transactions.c.id
                    == self.budgets_transactions.c.transaction_id,
                )
                .outerjoin(
                    self.budgets,
                    self.budgets_transactions.c.budget_id == self.budgets.c.id,
                )
                .where(self.transactions.c.occurred_at >= start.date())
                .where(self.transactions.c.occurred_at < end.date())
                .order_by(self.transactions.c.occurred_at.desc())
            ).fetchall()

            return Sqlite3.__rows_to_transaction_views(rows)

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
    def insert_plaid_account(self, token: str, institution_id: str) -> int:
        with self.engine.begin() as conn:
            result = conn.execute(
                insert(self.plaid_accounts)
                .values(token=token, institution_id=institution_id, cursor=None)
                .prefix_with("OR IGNORE")
            )
            if (
                result.inserted_primary_key
                and result.inserted_primary_key[0] is not None
            ):
                return result.inserted_primary_key[0]
            row = conn.execute(
                select(self.plaid_accounts.c.id).where(
                    self.plaid_accounts.c.institution_id == institution_id
                )
            ).first()
            return row.id

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

    def update_plaid_account_cursor(self, id: int, cursor: str | None):
        with self.engine.begin() as conn:
            conn.execute(
                update(self.plaid_accounts)
                .where(self.plaid_accounts.c.id == id)
                .values(cursor=cursor)
            )

    # MARK: - Plaid Categories
    def upsert_plaid_category(self, primary: str, detailed: str) -> int:
        with self.engine.begin() as conn:
            existing = conn.execute(
                select(self.plaid_categories.c.id)
                .where(self.plaid_categories.c.primary == primary)
                .where(self.plaid_categories.c.detailed == detailed)
                .limit(1)
            ).first()
            if existing:
                return existing.id

            result = conn.execute(
                insert(self.plaid_categories)
                .values(primary=primary, detailed=detailed)
                .prefix_with("OR IGNORE")
            )
            if (
                result.inserted_primary_key
                and result.inserted_primary_key[0] is not None
            ):
                return result.inserted_primary_key[0]

            existing = conn.execute(
                select(self.plaid_categories.c.id)
                .where(self.plaid_categories.c.primary == primary)
                .where(self.plaid_categories.c.detailed == detailed)
                .limit(1)
            ).first()
            if not existing:
                raise ValueError("Unable to upsert plaid category")
            return existing.id

    def retrieve_plaid_categories(self) -> list[PlaidCategory]:
        with self.engine.begin() as conn:
            return conn.execute(
                select(self.plaid_categories).order_by(self.plaid_categories.c.detailed)
            ).fetchall()

    def replace_budget_plaid_category_mappings(
        self, budget_id: int, plaid_category_ids: list[int]
    ):
        with self.engine.begin() as conn:
            conn.execute(
                delete(self.plaid_category_mappings).where(
                    self.plaid_category_mappings.c.budget_id == budget_id
                )
            )
            for category_id in plaid_category_ids:
                conn.execute(
                    insert(self.plaid_category_mappings)
                    .values(budget_id=budget_id, plaid_category_id=category_id)
                    .prefix_with("OR REPLACE")
                )

    def copy_budget_plaid_category_mappings(
        self, source_budget_id: int, target_budget_id: int
    ):
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(self.plaid_category_mappings.c.plaid_category_id).where(
                    self.plaid_category_mappings.c.budget_id == source_budget_id
                )
            ).fetchall()
            if not rows:
                return
            for (cat_id,) in rows:
                conn.execute(
                    insert(self.plaid_category_mappings).values(
                        budget_id=target_budget_id, plaid_category_id=cat_id
                    )
                )

    def retrieve_budget_plaid_category_mappings(
        self, budget_id: int
    ) -> list[PlaidCategoryMapping]:
        with self.engine.begin() as conn:
            rows = conn.execute(
                select(
                    self.plaid_category_mappings.c.id,
                    self.plaid_category_mappings.c.budget_id,
                    self.budgets.c.name.label("budget_name"),
                    self.plaid_categories.c.id.label("plaid_category_id"),
                    self.plaid_categories.c.primary.label("plaid_primary"),
                    self.plaid_categories.c.detailed.label("plaid_detailed"),
                )
                .join(
                    self.plaid_categories,
                    self.plaid_category_mappings.c.plaid_category_id
                    == self.plaid_categories.c.id,
                )
                .join(
                    self.budgets,
                    self.plaid_category_mappings.c.budget_id == self.budgets.c.id,
                )
                .where(self.plaid_category_mappings.c.budget_id == budget_id)
                .order_by(self.plaid_categories.c.detailed)
            ).fetchall()
            return [PlaidCategoryMapping(**dict(row._mapping)) for row in rows]

    def select_budget_id_by_plaid_category(self, category_key: str) -> int | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                select(self.plaid_category_mappings.c.budget_id)
                .join(
                    self.plaid_categories,
                    self.plaid_category_mappings.c.plaid_category_id
                    == self.plaid_categories.c.id,
                )
                .where(
                    (self.plaid_categories.c.detailed == category_key)
                    | (self.plaid_categories.c.primary == category_key)
                )
                .limit(1)
            ).first()
            return row.budget_id if row else None

    def select_budget_id_by_plaid_category_id(
        self, plaid_category_id: int
    ) -> int | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                select(self.plaid_category_mappings.c.budget_id)
                .where(
                    self.plaid_category_mappings.c.plaid_category_id
                    == plaid_category_id
                )
                .limit(1)
            ).first()
            return row.budget_id if row else None

    # MARK: - Accounts
    def account_exists_by_fingerprint(self, fingerprint: str) -> int | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                select(self.accounts.c.id)
                .where(self.accounts.c.fingerprint == fingerprint)
                .limit(1)
            ).first()

            return row.id if row else None

    def insert_account(self, obj: PartialAccount) -> int:
        values = {
            "name": obj.name,
            "external_id": obj.external_id,
            "source": obj.source,
            "account_type": obj.account_type,
            "fingerprint": obj.fingerprint,
            "balance": dollars_to_cents(obj.balance),
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
                insert(self.budgets_transactions)
                .values(transaction_id=transaction_id, budget_id=budget_id)
                .prefix_with("OR IGNORE")
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
            rows = conn.execute(
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
                    self.accounts, self.transactions.c.account_id == self.accounts.c.id
                )
                .outerjoin(
                    self.budgets,
                    self.budgets_transactions.c.budget_id == self.budgets.c.id,
                )
                .where(self.budgets_transactions.c.budget_id == budget_id)
                .order_by(self.transactions.c.occurred_at.desc())
            ).fetchall()

            return Sqlite3.__rows_to_transaction_views(rows)

    def select_budget_id_for_transaction(self, transaction_id: int) -> int | None:
        with self.engine.begin() as conn:
            row = conn.execute(
                select(self.budgets_transactions.c.budget_id)
                .where(self.budgets_transactions.c.transaction_id == transaction_id)
                .limit(1)
            ).first()

            return row.budget_id if row else None
