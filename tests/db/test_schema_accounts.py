import sqlite3
import pytest


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(open("schema/plaid_accounts.sql").read())
    conn.executescript(open("schema/accounts.sql").read())
    yield conn
    conn.close()


def test_insert_account(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ["Discover", "12234", "APPLE", "DEPOSITORY"],
    )

    row = db.execute("SELECT name FROM accounts").fetchone()

    assert row[0] == "Discover"


def test_source_enum_valid(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ["Discover", "12234", "APPLE", "DEPOSITORY"])
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ["Discover", "122345", "PLAID", "DEPOSITORY"])


def test_source_enum_invalid(db: sqlite3.Connection):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
            ["Discover", "12234", "EXT", "DEPOSITORY"])


def test_account_type_enum_valid(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ["Discover", "12234", "APPLE", "DEPOSITORY"])
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ["Discover", "122345", "PLAID", "CREDIT"])
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ["Discover", "1223456", "PLAID", "LOAN"])
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ["Discover", "1223457", "PLAID", "INVESTMENT"])


def test_account_type_enum_invalid(db: sqlite3.Connection):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
            ["Discover", "12234", "EXT", "EM"])


def test_select_account_by_id(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ["Savings", "ext-1", "APPLE", "DEPOSITORY"],
    )

    row = db.execute("SELECT id FROM accounts").fetchone()
    id = row[0]

    selected = db.execute(
        "SELECT name FROM accounts WHERE id = ?",
        (id, ),
    ).fetchone()

    assert selected is not None
    assert selected[0] == "Savings"


def test_get_all_accounts(db: sqlite3.Connection):
    accounts = ["Account One", "Account Two"]

    for name in accounts:
        db.execute(
            "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
            [name, f"ext-{name}", "APPLE", "DEPOSITORY"],
        )

    rows = db.execute("SELECT name FROM accounts ORDER BY id").fetchall()

    assert len(rows) == 2
    assert rows[0][0] == accounts[0]
    assert rows[1][0] == accounts[1]


def test_delete_account(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ["Temp Account", "ext-temp", "APPLE", "DEPOSITORY"],
    )

    row = db.execute("SELECT id FROM accounts").fetchone()
    id = row[0]

    db.execute(
        "DELETE FROM accounts WHERE id = ?",
        [id],
    )

    remaining = db.execute("SELECT * FROM accounts").fetchall()

    assert remaining == []


def test_autoincrement_id(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES ('A','ext-a','APPLE','DEPOSITORY');"
    )
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES ('B','ext-b','APPLE','DEPOSITORY');"
    )

    ids = [r[0] for r in db.execute("SELECT id FROM accounts ORDER BY id;")]
    assert ids == [1, 2]


def test_account_can_reference_plaid_account(db: sqlite3.Connection):
    # create plaid account
    db.execute(
        "INSERT INTO plaid_accounts (token) VALUES (?)",
        ["plaid-token-1"],
    )

    plaid_id = db.execute("SELECT id FROM plaid_accounts").fetchone()[0]

    # create account referencing plaid account
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, plaid_id) VALUES (?,?,?,?,?)",
        ("Main Checking", "ext-plaid-1", "PLAID", "DEPOSITORY", plaid_id),
    )

    row = db.execute("SELECT name, plaid_id FROM accounts").fetchone()

    assert row is not None
    assert row[0] == "Main Checking"
    assert row[1] == plaid_id


def test_account_rejects_invalid_plaid_id(db: sqlite3.Connection):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO accounts (name, external_id, source, account_type, plaid_id) VALUES (?,?,?,?,?)",
            ("Invalid Account", "ext-invalid", "APPLE", "DEPOSITORY", 999),
        )


def test_cascade_delete_plaid_account_removes_accounts(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO plaid_accounts (token) VALUES (?)",
        ["plaid-token-2"],
    )

    plaid_id = db.execute("SELECT id FROM plaid_accounts").fetchone()[0]

    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, plaid_id) VALUES (?, ?, ?, ?, ?)",
        ("Savings Account", "1234", "APPLE", "DEPOSITORY", plaid_id),
    )

    # delete plaid account
    db.execute(
        "DELETE FROM plaid_accounts WHERE id = ?",
        (plaid_id, ),
    )

    rows = db.execute("SELECT * FROM accounts").fetchall()

    assert rows == []
