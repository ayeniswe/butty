import pytest
from sqlalchemy import select

from datastore.db import Sqlite3
from datastore.model import (
    Budget,
    PartialTransaction,
    PartialAccount,
    Tag,
    TransactionDirection,
    TransactionSource,
)


@pytest.fixture
def db():
    db = Sqlite3(":memory:")
    yield db


# --------------------
# Budget APIs
# --------------------


def test_insert_budget(db: Sqlite3):
    db.insert_budget("Food", 500)

    with db.engine.begin() as conn:
        row = conn.execute(select(db.budgets)).first()

    assert row.name == "Food"
    assert row.amount_allocated == 500.0
    assert row.amount_spent == 0
    assert row.amount_saved == 0.0


def test_update_budget_updates_amount_saved(db: Sqlite3):
    db.insert_budget("Rent", 1000)

    with db.engine.begin() as conn:
        row = conn.execute(select(db.budgets)).first()

        updated = Budget(
            id=row.id,
            name="Rent",
            amount_allocated=1200,
            amount_spent=200,
            amount_saved=0,  # trigger should overwrite
            level="HIGH",
        )

        db.update_budget(updated)

        row = conn.execute(select(db.budgets)).first()

    assert row.amount_saved == 1000


def test_delete_budget(db: Sqlite3):
    db.insert_budget("Temp")

    with db.engine.begin() as conn:
        row = conn.execute(select(db.budgets)).first()

        db.delete_budget(row.id)

        assert conn.execute(select(db.budgets)).first() is None


def test_select_budget(db: Sqlite3):
    db.insert_budget("Temp")
    db.select_budget(1) is not None


def test_get_budgets(db: Sqlite3):
    db.insert_budget("Temp")
    db.insert_budget("Temp")
    db.insert_budget("Temp")
    assert len(db.get_budgets()) == 3


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
            PartialTransaction("Coffee",
                               45,
                               TransactionDirection.OUT,
                               external_id="ext-45",
                               account_id=1))
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
        PartialTransaction("Salary",
                           3000,
                           TransactionDirection.IN,
                           occurred_at=ts,
                           account_id=1))
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
        PartialTransaction("Groceries",
                           50,
                           TransactionDirection.OUT,
                           account_id=1), )
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
        PartialTransaction("Delete Me",
                           1,
                           TransactionDirection.OUT,
                           account_id=1), )
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
        PartialTransaction("Trans",
                           100,
                           TransactionDirection.OUT,
                           account_id=1), )
    db.select_transaction(1) is not None


def test_get_transactions(db: Sqlite3):
    db.insert_account(
        PartialAccount(
            name="Default Account",
            external_id="ext-acc-1",
            source=TransactionSource.APPLE,
            account_type="DEPOSITORY",
        )
    )
    db.insert_transaction(
        PartialTransaction("Trans 1",
                           1,
                           TransactionDirection.OUT,
                           account_id=1), )
    db.insert_transaction(
        PartialTransaction("Trans 2", 2, TransactionDirection.IN,
                           account_id=1), )
    db.insert_transaction(
        PartialTransaction("Trans 3",
                           3,
                           TransactionDirection.OUT,
                           account_id=1), )
    assert len(db.get_transactions()) == 3


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
    db.select_tag(1) is not None


def test_get_tags(db: Sqlite3):
    db.insert_tag("Tag 1")
    db.insert_tag("Tag 2")
    db.insert_tag("Tag 3")
    assert len(db.get_tags()) == 3


# --------------------
# Budget <-> Tag APIs
# --------------------


def test_tag_budget(db: Sqlite3):
    db.insert_budget("Food")
    db.insert_tag("Essential")

    with db.engine.begin() as conn:
        budget = conn.execute(select(db.budgets)).first()
        tag = conn.execute(select(db.tags)).first()

        db.tag_budget(budget.id, tag.id)

    assert 1 == budget.id
    assert 1 == tag.id


def test_untag_budget(db: Sqlite3):
    db.insert_budget("Food")
    db.insert_tag("Essential")

    with db.engine.begin() as conn:
        db.tag_budget(1, 1)
        db.untag_budget(1, 1)

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


def test_get_accounts(db: Sqlite3):
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

    accounts = db.get_accounts()

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


def test_get_plaid_accounts(db: Sqlite3):
    db.insert_plaid_account("t1")
    db.insert_plaid_account("t2")
    db.insert_plaid_account("t3")

    accounts = db.get_plaid_accounts()

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
