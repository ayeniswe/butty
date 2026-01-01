import sqlite3

import pytest


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(open("schema/budgets.sql").read())
    conn.executescript(open("schema/accounts.sql").read())
    conn.executescript(open("schema/plaid_accounts.sql").read())
    conn.executescript(open("schema/budgets_transactions.sql").read())
    conn.executescript(open("schema/transactions.sql").read())
    yield conn
    conn.close()


def test_insert_budget_transaction_link(db: sqlite3.Connection):
    # create budget
    db.execute(
        "INSERT INTO budgets (name, amount_allocated) VALUES (?, ?)",
        ("Groceries", 500),
    )
    budget_id = db.execute("SELECT id FROM budgets").fetchone()[0]

    # create account
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance) VALUES (?,?,?,?,?)",
        ("Checking", "ext-1", "APPLE", "DEPOSITORY", 0),
    )
    account_id = db.execute("SELECT id FROM accounts").fetchone()[0]

    # create transaction
    db.execute(
        """
        INSERT INTO transactions (account_id, name, amount, direction, occurred_at)
        VALUES (?,?,?,?,?)
        """,
        (account_id, "Walmart", 120.50, "OUT", "2025-01-01"),
    )
    transaction_id = db.execute("SELECT id FROM transactions").fetchone()[0]

    # link transaction to budget
    db.execute(
        """
        INSERT INTO budgets_transactions (transaction_id, budget_id)
        VALUES (?,?)
        """,
        (transaction_id, budget_id),
    )

    row = db.execute(
        "SELECT transaction_id, budget_id FROM budgets_transactions"
    ).fetchone()

    assert row == (transaction_id, budget_id)


def test_budget_transaction_rejects_invalid_budget(db: sqlite3.Connection):
    # create account + transaction
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance) VALUES (?,?,?,?,?)",
        ("Checking", "ext-2", "APPLE", "DEPOSITORY", 0),
    )
    account_id = db.execute("SELECT id FROM accounts").fetchone()[0]

    db.execute(
        """
        INSERT INTO transactions (account_id, name, amount, direction, occurred_at)
        VALUES (?,?,?,?,?)
        """,
        (account_id, "Target", 50.00, "OUT", "2025-01-02"),
    )
    transaction_id = db.execute("SELECT id FROM transactions").fetchone()[0]

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO budgets_transactions (transaction_id, budget_id) VALUES (?, ?)",
            (transaction_id, 999),
        )


def test_budget_transaction_rejects_invalid_transaction(db: sqlite3.Connection):
    # create budget only
    db.execute(
        "INSERT INTO budgets (name, amount_allocated) VALUES (?, ?)",
        ("Utilities", 300),
    )
    budget_id = db.execute("SELECT id FROM budgets").fetchone()[0]

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO budgets_transactions (transaction_id, budget_id) VALUES (?, ?)",
            (999, budget_id),
        )


def test_budget_transaction_composite_pk_enforced(db: sqlite3.Connection):
    # setup budget
    db.execute(
        "INSERT INTO budgets (name, amount_allocated) VALUES (?, ?)",
        ("Rent", 1500),
    )
    budget_id = db.execute("SELECT id FROM budgets").fetchone()[0]

    # setup account + transaction
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance) VALUES (?,?,?,?,?)",
        ("Checking", "ext-3", "APPLE", "DEPOSITORY", 0),
    )
    account_id = db.execute("SELECT id FROM accounts").fetchone()[0]

    db.execute(
        """
        INSERT INTO transactions (account_id, name, amount, direction, occurred_at)
        VALUES (?,?,?,?,?)
        """,
        (account_id, "Landlord", 1500, "OUT", "2025-01-03"),
    )
    transaction_id = db.execute("SELECT id FROM transactions").fetchone()[0]

    # first insert works
    db.execute(
        "INSERT INTO budgets_transactions (transaction_id, budget_id) VALUES (?,?)",
        (transaction_id, budget_id),
    )

    # duplicate should fail due to composite PK
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO budgets_transactions (transaction_id, budget_id) VALUES (?,?)",
            (transaction_id, budget_id),
        )


def test_cascade_delete_budget_removes_budget_transactions(db: sqlite3.Connection):
    # create budget
    db.execute(
        "INSERT INTO budgets (name, amount_allocated) VALUES (?, ?)",
        ("Dining", 400),
    )
    budget_id = db.execute("SELECT id FROM budgets").fetchone()[0]

    # create account + transaction
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance) VALUES (?,?,?,?,?)",
        ("Checking", "ext-4", "APPLE", "DEPOSITORY", 0),
    )
    account_id = db.execute("SELECT id FROM accounts").fetchone()[0]

    db.execute(
        """
        INSERT INTO transactions (account_id, name, amount, direction, occurred_at)
        VALUES (?,?,?,?,?)
        """,
        (account_id, "Restaurant", 80, "OUT", "2025-01-04"),
    )
    transaction_id = db.execute("SELECT id FROM transactions").fetchone()[0]

    # link
    db.execute(
        "INSERT INTO budgets_transactions (transaction_id, budget_id) VALUES (?,?)",
        (transaction_id, budget_id),
    )

    # delete budget
    db.execute(
        "DELETE FROM budgets WHERE id = ?",
        (budget_id,),
    )

    rows = db.execute("SELECT * FROM budgets_transactions").fetchall()

    assert rows == []


def test_cascade_delete_transaction_removes_budget_transactions(db: sqlite3.Connection):
    # create budget
    db.execute(
        "INSERT INTO budgets (name, amount_allocated) VALUES (?, ?)",
        ("Fuel", 250),
    )
    budget_id = db.execute("SELECT id FROM budgets").fetchone()[0]

    # create account
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance) VALUES (?,?,?,?,?)",
        ("Checking", "ext-5", "APPLE", "DEPOSITORY", 0),
    )
    account_id = db.execute("SELECT id FROM accounts").fetchone()[0]

    # create transaction
    db.execute(
        """
        INSERT INTO transactions (account_id, name, amount, direction, occurred_at)
        VALUES (?,?,?,?,?)
        """,
        (account_id, "Gas Station", 60, "OUT", "2025-01-05"),
    )
    transaction_id = db.execute("SELECT id FROM transactions").fetchone()[0]

    # link transaction to budget
    db.execute(
        "INSERT INTO budgets_transactions (transaction_id, budget_id) VALUES (?,?)",
        (transaction_id, budget_id),
    )

    # delete transaction
    db.execute(
        "DELETE FROM transactions WHERE id = ?",
        (transaction_id,),
    )

    rows = db.execute("SELECT * FROM budgets_transactions").fetchall()

    assert rows == []
