import datetime as dt
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from api.datastore.db import Sqlite3
from api.datastore.model import (
    PartialAccount,
    PartialBudget,
    PartialTransaction,
    Tag,
    TransactionDirection,
    TransactionSource,
)


@pytest.fixture
def db():
    db = Sqlite3(":memory:")
    yield db
    db.engine.dispose()


# --------------------
# Budget APIs
# --------------------


def test_insert_budget(db: Sqlite3):
    db.insert_budget("Food", 500, datetime(2020, 1, 1))

    with db.engine.begin() as conn:
        row = conn.execute(select(db.budgets)).first()

    assert row.name == "Food"
    assert row.amount_allocated == 50000
    assert row.amount_spent == 0
    assert row.amount_saved == 0.0
    assert row.created_at == datetime(2020, 1, 1).isoformat()


def test_update_budget_updates_amount_saved(db: Sqlite3):
    db.insert_budget("Rent", 1000)

    with db.engine.begin() as conn:
        row = conn.execute(select(db.budgets)).first()

        updated = PartialBudget(
            id=row.id,
            name="Rent",
            amount_allocated=12.00,
            amount_spent=200,
            level="HIGH",
        )

        db.update_budget(updated)

        row = conn.execute(select(db.budgets)).first()

    assert row.amount_saved == 1000


def test_delete_budget(db: Sqlite3):
    db.insert_budget("Temp", 100)

    with db.engine.begin() as conn:
        row = conn.execute(select(db.budgets)).first()

        db.delete_budget(row.id)

        assert conn.execute(select(db.budgets)).first() is None


def test_select_budget(db: Sqlite3):
    db.insert_budget("Temp", 100)
    assert db.select_budget(1) is not None


def test_retrieve_budgets(db: Sqlite3):
    db.insert_budget("Temp", 100)
    db.insert_budget("Temp", 100)
    db.insert_budget("Temp", 100)
    assert len(db.retrieve_budgets()) == 3


def test_filter_budgets_by_created_at_range(db: Sqlite3):
    # insert budgets at different times
    db.insert_budget("Old Budget", 100)
    db.insert_budget("Mid Budget", 200)
    db.insert_budget("New Budget", 300)

    with db.engine.begin() as conn:
        rows = conn.execute(select(db.budgets)).fetchall()
        assert len(rows) == 3

        # manually update created_at to controlled values
        now = datetime.now(dt.UTC)
        old = now - timedelta(days=10)
        mid = now - timedelta(days=5)
        new = now - timedelta(days=1)

        conn.execute(
            db.budgets.update()
            .where(db.budgets.c.name == "Old Budget")
            .values(created_at=old.isoformat())
        )
        conn.execute(
            db.budgets.update()
            .where(db.budgets.c.name == "Mid Budget")
            .values(created_at=mid.isoformat())
        )
        conn.execute(
            db.budgets.update()
            .where(db.budgets.c.name == "New Budget")
            .values(created_at=new.isoformat())
        )

    # filter only mid -> new
    start = now - timedelta(days=6)
    end = now

    result = db.filter_budgets(start, end)

    names = {b.name for b in result}

    assert "Mid Budget" in names
    assert "New Budget" in names
    assert "Old Budget" not in names


# --------------------
# Transaction APIs
# --------------------


def test_insert_transaction_uses_db_default_occurred_at(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="Default Account",
            external_id="ext-acc-1",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )
    with db.engine.begin() as conn:
        db.insert_transaction(
            PartialTransaction(
                "Coffee",
                45,
                TransactionDirection.OUT,
                external_id="ext-45",
                account_id=1,
            )
        )
        row = conn.execute(select(db.transactions)).first()

    assert row.occurred_at is not None


def test_insert_transaction_with_explicit_occurred_at(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="Default Account",
            external_id="ext-acc-1",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )
    ts = "2024-01-01 10:00:00"
    db.insert_transaction(
        PartialTransaction(
            "Salary", 3000, TransactionDirection.IN, occurred_at=ts, account_id=1
        )
    )
    with db.engine.begin() as conn:
        row = conn.execute(select(db.transactions)).first()

    assert row.occurred_at == ts


def test_update_transaction_note(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="Default Account",
            external_id="ext-acc-1",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )
    db.insert_transaction(
        PartialTransaction("Groceries", 50, TransactionDirection.OUT, account_id=1),
    )
    with db.engine.begin() as conn:
        row = conn.execute(select(db.transactions)).first()

        db.update_transaction_note(row.id, "Walmart")

        row = conn.execute(select(db.transactions)).first()

    assert row.note == "Walmart"


def test_delete_transaction(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="Default Account",
            external_id="ext-acc-1",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )
    db.insert_transaction(
        PartialTransaction("Delete Me", 1, TransactionDirection.OUT, account_id=1),
    )
    db.delete_transaction(1)

    with db.engine.begin() as conn:
        assert conn.execute(select(db.transactions)).first() is None


def test_select_transaction(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="Default Account",
            external_id="ext-acc-1",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )
    db.insert_transaction(
        PartialTransaction("Trans", 100, TransactionDirection.OUT, account_id=1),
    )
    assert db.select_transaction(1) is not None


def test_retrieve_transactions(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="Default Account",
            external_id="ext-acc-1",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )
    db.insert_transaction(
        PartialTransaction("Trans 1", 1, TransactionDirection.OUT, account_id=1),
    )
    db.insert_transaction(
        PartialTransaction("Trans 2", 2, TransactionDirection.IN, account_id=1),
    )
    db.insert_transaction(
        PartialTransaction("Trans 3", 3, TransactionDirection.OUT, account_id=1),
    )
    assert len(db.retrieve_transactions()) == 3


def test_filter_transactions_by_occurred_at_range(db: Sqlite3):
    # create account
    db.insert_account(
        PartialAccount(
            name="Default Account",
            external_id="ext-filter",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )

    # insert transactions
    db.insert_transaction(
        PartialTransaction(
            name="Old Tx",
            amount=10,
            direction=TransactionDirection.OUT,
            account_id=1,
        )
    )
    db.insert_transaction(
        PartialTransaction(
            name="Mid Tx",
            amount=20,
            direction=TransactionDirection.OUT,
            account_id=1,
        )
    )
    db.insert_transaction(
        PartialTransaction(
            name="New Tx",
            amount=30,
            direction=TransactionDirection.OUT,
            account_id=1,
        )
    )

    with db.engine.begin() as conn:
        rows = conn.execute(select(db.transactions)).fetchall()
        assert len(rows) == 3

        now = datetime.now(dt.UTC)
        old = now - timedelta(days=10)
        mid = now - timedelta(days=5)
        new = now - timedelta(days=1)

        conn.execute(
            db.transactions.update()
            .where(db.transactions.c.name == "Old Tx")
            .values(occurred_at=old.isoformat())
        )
        conn.execute(
            db.transactions.update()
            .where(db.transactions.c.name == "Mid Tx")
            .values(occurred_at=mid.isoformat())
        )
        conn.execute(
            db.transactions.update()
            .where(db.transactions.c.name == "New Tx")
            .values(occurred_at=new.isoformat())
        )

    # filter mid -> new
    start = now - timedelta(days=6)
    end = now

    result = db.filter_transactions(start, end)
    names = {t.name for t in result}

    assert "Mid Tx" in names
    assert "New Tx" in names
    assert "Old Tx" not in names


# # --------------------
# # Tag APIs
# # --------------------


def test_insert_tag(db: Sqlite3):
    db.insert_tag("Essential")
    with db.engine.begin() as conn:
        row = conn.execute(select(db.tags)).first()

    assert row.name == "Essential"


def test_update_tag(db: Sqlite3):
    db.insert_tag("Old")
    with db.engine.begin() as conn:
        row = conn.execute(select(db.tags)).first()

        db.update_tag(Tag(id=row.id, name="New"))

        row = conn.execute(select(db.tags)).first()
    assert row.name == "New"


def test_delete_tag(db: Sqlite3):
    db.insert_tag("Temp")
    with db.engine.begin() as conn:
        row = conn.execute(select(db.tags)).first()

        db.delete_tag(row.id)

        assert conn.execute(select(db.tags)).first() is None


def test_select_tag(db: Sqlite3):
    db.insert_tag("Tag")
    assert db.select_tag(1) is not None


def test_retrieve_tags(db: Sqlite3):
    db.insert_tag("Tag 1")
    db.insert_tag("Tag 2")
    db.insert_tag("Tag 3")
    assert len(db.retrieve_tags()) == 3


# --------------------
# Budget <-> Tag APIs
# --------------------


def test_insert_budget_tag(db: Sqlite3):
    db.insert_budget("Food", 100)
    db.insert_tag("Essential")

    with db.engine.begin() as conn:
        budget = conn.execute(select(db.budgets)).first()
        tag = conn.execute(select(db.tags)).first()

        db.insert_budget_tag(budget.id, tag.id)

    assert 1 == budget.id
    assert 1 == tag.id


def test_delete_budget_tag(db: Sqlite3):
    db.insert_budget("Food", 100)
    db.insert_tag("Essential")

    with db.engine.begin() as conn:
        db.insert_budget_tag(1, 1)
        db.delete_budget_tag(1, 1)

        assert conn.execute(select(db.budgets_tags)).first() is None


# --------------------
# Account APIs
# --------------------


def test_insert_account_without_plaid_id(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="Manual Account",
            external_id="ext-manual",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )

    with db.engine.begin() as conn:
        row = conn.execute(select(db.accounts)).first()

    assert row is not None
    assert row.name == "Manual Account"
    assert row.plaid_id is None


def test_insert_account_with_plaid_id(db: Sqlite3):
    db.insert_plaid_account("token-acc")

    db.insert_account(
        PartialAccount(
            name="Linked Account",
            external_id="ext-plaid-1",
            source="PLAID",
            plaid_id=1,
            account_type="DEPOSITORY",
        )
    )

    with db.engine.begin() as conn:
        row = conn.execute(select(db.accounts)).first()

    assert row is not None
    assert row.name == "Linked Account"
    assert row.plaid_id == 1


def test_select_account(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="Select Me",
            external_id="ext-sel",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )

    account = db.select_account(1)

    assert account is not None
    assert account.id == 1
    assert account.name == "Select Me"


def test_select_account_by_ext_id(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="Select Me",
            external_id="ext-sel",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )

    account = db.select_account_by_ext_id("ext-sel")

    assert account is not None
    assert account.id == 1
    assert account.name == "Select Me"


def test_retrieve_accounts(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="Account One",
            external_id="ext-1",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )
    db.insert_account(
        PartialAccount(
            name="Account Two",
            external_id="ext-2",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )
    db.insert_account(
        PartialAccount(
            name="Account Three",
            external_id="ext-3",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )

    accounts = db.retrieve_accounts()

    assert len(accounts) == 3
    assert accounts[0].name == "Account One"
    assert accounts[1].name == "Account Two"
    assert accounts[2].name == "Account Three"


def test_delete_account(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="Delete Me",
            external_id="ext-del",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )

    db.delete_account(1)

    with db.engine.begin() as conn:
        row = conn.execute(select(db.accounts)).first()

    assert row is None


# --------------------
# Plaid Account APIs
# --------------------


def test_insert_plaid_account(db: Sqlite3):
    db.insert_plaid_account("token-123")

    with db.engine.begin() as conn:
        row = conn.execute(select(db.plaid_accounts)).first()

    assert row is not None
    assert row.token == "token-123"


def test_select_plaid_account(db: Sqlite3):
    db.insert_plaid_account("token-abc")

    account = db.select_plaid_account(1)

    assert account is not None
    assert account.id == 1
    assert account.token == "token-abc"


def test_retrieve_plaid_accounts(db: Sqlite3):
    db.insert_plaid_account("t1")
    db.insert_plaid_account("t2")
    db.insert_plaid_account("t3")

    accounts = db.retrieve_plaid_accounts()

    assert len(accounts) == 3
    assert accounts[0].token == "t1"
    assert accounts[1].token == "t2"
    assert accounts[2].token == "t3"


def test_delete_plaid_account(db: Sqlite3):
    db.insert_plaid_account("delete-me")

    db.delete_plaid_account(1)

    with db.engine.begin() as conn:
        row = conn.execute(select(db.plaid_accounts)).first()

    assert row is None


# --------------------
# Budget <-> Transaction APIs
# --------------------


def test_insert_budget_transaction_link(db: Sqlite3):
    # create budget
    db.insert_budget("Groceries", 500)

    # create account
    db.insert_account(
        PartialAccount(
            name="Checking",
            external_id="ext-bt-1",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )

    # create transaction
    db.insert_transaction(
        PartialTransaction(
            name="Walmart",
            amount=120,
            direction=TransactionDirection.OUT,
            account_id=1,
        )
    )

    with db.engine.begin() as conn:
        budget_id = conn.execute(select(db.budgets)).first().id
        transaction_id = conn.execute(select(db.transactions)).first().id

        db.insert_budget_transaction(budget_id, transaction_id)

        row = conn.execute(select(db.budgets_transactions)).first()
        assert row is not None
        assert row.budget_id == budget_id
        assert row.transaction_id == transaction_id


def test_delete_budget_transaction_link(db: Sqlite3):
    # create budget
    db.insert_budget("Groceries", 500)

    # create account
    db.insert_account(
        PartialAccount(
            name="Checking",
            external_id="ext-bt-1",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )

    # create transaction
    db.insert_transaction(
        PartialTransaction(
            name="Walmart",
            amount=120,
            direction=TransactionDirection.OUT,
            account_id=1,
        )
    )

    with db.engine.begin() as conn:
        budget_id = conn.execute(select(db.budgets)).first().id
        transaction_id = conn.execute(select(db.transactions)).first().id

        # pre-link
        db.insert_budget_transaction(budget_id, transaction_id)
        assert conn.execute(select(db.budgets_transactions)).first() is not None

        # delete link
        db.delete_budget_transaction(budget_id, transaction_id)

        assert conn.execute(select(db.budgets_transactions)).first() is None


# --------------------
# Insert Return Value Coverage
# --------------------


def test_insert_tag_returns_id(db: Sqlite3):
    tag_id = db.insert_tag("ReturnID")
    assert tag_id == 1


def test_insert_account_returns_id(db: Sqlite3):
    account_id = db.insert_account(
        PartialAccount(
            name="Return Account",
            external_id="ret-1",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )
    assert account_id == 1


def test_insert_transaction_returns_id(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="Tx Account",
            external_id="ret-tx",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )

    tx_id = db.insert_transaction(
        PartialTransaction(
            name="Tx",
            amount=10,
            direction=TransactionDirection.OUT,
            account_id=1,
            note="For TX tests",
        )
    )
    assert tx_id == 1


# --------------------
# Account Selection Coverage
# --------------------


def test_select_account_by_id(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="By ID",
            external_id="by-id",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )

    account = db.select_account_by_id(1)

    assert account is not None
    assert account.id == 1
    assert account.name == "By ID"


# --------------------
# Budget <-> Tag Retrieval Coverage
# --------------------


def test_retrieve_budget_tags(db: Sqlite3):
    db.insert_budget("Food", 100)
    db.insert_tag("Essential")
    db.insert_tag("Groceries")

    with db.engine.begin():
        db.insert_budget_tag(1, 1)
        db.insert_budget_tag(1, 2)

    tags = db.retrieve_budget_tags(1)
    names = {t.name for t in tags}

    assert names == {"Essential", "Groceries"}


# --------------------
# Budget <-> Transaction View Coverage
# --------------------


def test_retrieve_budget_transactions_view(db: Sqlite3):
    db.insert_budget("Groceries", 500)

    db.insert_account(
        PartialAccount(
            name="Checking",
            external_id="view-acc",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )

    db.insert_transaction(
        PartialTransaction(
            name="Old Tx",
            amount=10,
            direction=TransactionDirection.OUT,
            account_id=1,
            occurred_at="2024-01-01",
        )
    )

    db.insert_transaction(
        PartialTransaction(
            name="New Tx",
            amount=20,
            direction=TransactionDirection.OUT,
            account_id=1,
            occurred_at="2024-02-01",
        )
    )

    with db.engine.begin():
        db.insert_budget_transaction(1, 1)
        db.insert_budget_transaction(1, 2)

    rows = db.retrieve_budget_transactions(1)

    assert len(rows) == 2

    # ordered DESC by occurred_at
    assert rows[0].name == "New Tx"
    assert rows[1].name == "Old Tx"

    # joined account name present
    assert rows[0].account_name == "Checking"
