import sqlite3
import pytest


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(open("schema/plaid_accounts.sql").read())
    yield conn
    conn.close()


def test_insert_plaid_account(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO plaid_accounts (token, name) VALUES (?, ?)",
        ("test-token-123", "Checking Account"),
    )

    row = db.execute(
        "SELECT token, name FROM plaid_accounts"
    ).fetchone()

    assert row is not None
    assert row[0] == "test-token-123"
    assert row[1] == "Checking Account"


def test_select_plaid_account_by_id(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO plaid_accounts (token, name) VALUES (?, ?)",
        ("token-abc", "Savings"),
    )

    row = db.execute(
        "SELECT id FROM plaid_accounts"
    ).fetchone()
    plaid_id = row[0]

    selected = db.execute(
        "SELECT id, token, name FROM plaid_accounts WHERE id = ?",
        (plaid_id,),
    ).fetchone()

    assert selected is not None
    assert selected[0] == plaid_id
    assert selected[1] == "token-abc"
    assert selected[2] == "Savings"


def test_get_all_plaid_accounts(db: sqlite3.Connection):
    accounts = [
        ("t1", "Account One"),
        ("t2", "Account Two"),
    ]

    for token, name in accounts:
        db.execute(
            "INSERT INTO plaid_accounts (token, name) VALUES (?, ?)",
            (token, name),
        )

    rows = db.execute(
        "SELECT token, name FROM plaid_accounts ORDER BY id"
    ).fetchall()

    assert len(rows) == 2
    assert rows[0] == accounts[0]
    assert rows[1] == accounts[1]


def test_delete_plaid_account(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO plaid_accounts (token, name) VALUES (?, ?)",
        ("delete-me", "Temp Account"),
    )

    row = db.execute(
        "SELECT id FROM plaid_accounts"
    ).fetchone()
    plaid_id = row[0]

    db.execute(
        "DELETE FROM plaid_accounts WHERE id = ?",
        (plaid_id,),
    )

    remaining = db.execute(
        "SELECT * FROM plaid_accounts"
    ).fetchall()

    assert remaining == []


def test_autoincrement_id(db: sqlite3.Connection):
    db.execute("INSERT INTO plaid_accounts (name, token) VALUES ('A', '12323');")
    db.execute("INSERT INTO plaid_accounts (name, token) VALUES ('B', '12334');")

    ids = [r[0] for r in db.execute("SELECT id FROM plaid_accounts ORDER BY id;")]
    assert ids == [1, 2]