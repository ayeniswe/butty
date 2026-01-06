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
        "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES (?,?,?,?,?,?)",
        ["Discover", "12234", "APPLE", "DEPOSITORY", 0, "fp-discover-1"],
    )

    row = db.execute("SELECT name FROM accounts").fetchone()

    assert row[0] == "Discover"


def test_source_enum_valid(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES (?,?,?,?,?,?)",
        ["Discover", "12234", "APPLE", "DEPOSITORY", 0, "fp-source-valid-1"],
    )
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES (?,?,?,?,?,?)",
        ["Discover", "122345", "PLAID", "DEPOSITORY", 0, "fp-source-valid-2"],
    )


def test_source_enum_invalid(db: sqlite3.Connection):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES (?,?,?,?,?,?)",
            ["Discover", "12234", "EXT", "DEPOSITORY", 0, "fp-source-invalid-1"],
        )


def test_account_type_enum_valid(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES (?,?,?,?,?,?)",
        ["Discover", "12234", "APPLE", "DEPOSITORY", 0, "fp-type-valid-1"],
    )
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES (?,?,?,?,?,?)",
        ["Discover", "122345", "PLAID", "CREDIT", 0, "fp-type-valid-2"],
    )
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES (?,?,?,?,?,?)",
        ["Discover", "1223456", "PLAID", "LOAN", 0, "fp-type-valid-3"],
    )
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES (?,?,?,?,?,?)",
        ["Discover", "1223457", "PLAID", "INVESTMENT", 0, "fp-type-valid-4"],
    )


def test_account_type_enum_invalid(db: sqlite3.Connection):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES (?,?,?,?,?,?)",
            ["Discover", "12234", "EXT", "EM", 0, "fp-type-invalid-1"],
        )


def test_select_account_by_id(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES (?,?,?,?,?,?)",
        ["Savings", "ext-1", "APPLE", "DEPOSITORY", 0, "fp-select-1"],
    )

    row = db.execute("SELECT id FROM accounts").fetchone()
    id = row[0]

    selected = db.execute(
        "SELECT name FROM accounts WHERE id = ?",
        (id,),
    ).fetchone()

    assert selected is not None
    assert selected[0] == "Savings"


def test_get_all_accounts(db: sqlite3.Connection):
    accounts = ["Account One", "Account Two"]

    for idx, name in enumerate(accounts):
        db.execute(
            "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES (?,?,?,?,?,?)",
            [name, f"ext-{name}", "APPLE", "DEPOSITORY", 0, f"fp-getall-{idx + 1}"],
        )

    rows = db.execute("SELECT name FROM accounts ORDER BY id").fetchall()

    assert len(rows) == 2
    assert rows[0][0] == accounts[0]
    assert rows[1][0] == accounts[1]


def test_delete_account(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES (?,?,?,?,?,?)",
        ["Temp Account", "ext-temp", "APPLE", "DEPOSITORY", 0, "fp-delete-1"],
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
        "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES ('A','ext-a','APPLE','DEPOSITORY',0,'fp-auto-1');"
    )
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint) VALUES ('B','ext-b','APPLE','DEPOSITORY',0,'fp-auto-2');"
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
        "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint, plaid_id) VALUES (?,?,?,?,?,?,?)",
        (
            "Main Checking",
            "ext-plaid-1",
            "PLAID",
            "DEPOSITORY",
            0,
            "fp-auto-1",
            plaid_id,
        ),
    )

    row = db.execute("SELECT name, plaid_id FROM accounts").fetchone()

    assert row is not None
    assert row[0] == "Main Checking"
    assert row[1] == plaid_id


def test_account_rejects_invalid_plaid_id(db: sqlite3.Connection):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint, plaid_id) VALUES (?,?,?,?,?,?,?)",
            (
                "Invalid Account",
                "ext-invalid",
                "APPLE",
                "DEPOSITORY",
                "fp-auto-1",
                0,
                999,
            ),
        )


def test_cascade_delete_plaid_account_removes_accounts(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO plaid_accounts (token) VALUES (?)",
        ["plaid-token-2"],
    )

    plaid_id = db.execute("SELECT id FROM plaid_accounts").fetchone()[0]

    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type, balance, fingerprint, plaid_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("Savings Account", "1234", "APPLE", "DEPOSITORY", 0, "fp-auto-1", plaid_id),
    )

    # delete plaid account
    db.execute(
        "DELETE FROM plaid_accounts WHERE id = ?",
        (plaid_id,),
    )

    rows = db.execute("SELECT * FROM accounts").fetchall()

    assert rows == []
