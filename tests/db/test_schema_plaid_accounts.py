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
        "INSERT INTO plaid_accounts (token) VALUES (?)",
        ["test-token-123"],
    )

    row = db.execute("SELECT token FROM plaid_accounts").fetchone()

    assert row is not None
    assert row[0] == "test-token-123"


def test_select_plaid_account_by_id(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO plaid_accounts (token) VALUES (?)",
        ["token-abc"],
    )

    row = db.execute("SELECT id FROM plaid_accounts").fetchone()
    plaid_id = row[0]

    selected = db.execute(
        "SELECT id, token FROM plaid_accounts WHERE id = ?",
        (plaid_id, ),
    ).fetchone()

    assert selected is not None
    assert selected[0] == plaid_id
    assert selected[1] == "token-abc"


def test_get_all_plaid_accounts(db: sqlite3.Connection):
    accounts = [
        "t1",
        "t2",
    ]

    for token in accounts:
        db.execute(
            "INSERT INTO plaid_accounts (token) VALUES (?)",
            [token],
        )

    rows = db.execute(
        "SELECT token FROM plaid_accounts ORDER BY id").fetchall()

    assert len(rows) == 2
    assert rows[0][0] == accounts[0]
    assert rows[1][0] == accounts[1]


def test_delete_plaid_account(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO plaid_accounts (token) VALUES (?)",
        ["delete-me"],
    )

    row = db.execute("SELECT id FROM plaid_accounts").fetchone()
    plaid_id = row[0]

    db.execute(
        "DELETE FROM plaid_accounts WHERE id = ?",
        (plaid_id, ),
    )

    remaining = db.execute("SELECT * FROM plaid_accounts").fetchall()

    assert remaining == []


def test_autoincrement_id(db: sqlite3.Connection):
    db.execute("INSERT INTO plaid_accounts ( token) VALUES ( '12323');")
    db.execute("INSERT INTO plaid_accounts ( token) VALUES ( '12334');")

    ids = [
        r[0] for r in db.execute("SELECT id FROM plaid_accounts ORDER BY id;")
    ]
    assert ids == [1, 2]
