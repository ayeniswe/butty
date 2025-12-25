import sqlite3
import pytest


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(open("schema/accounts.sql").read())
    conn.executescript(open("schema/transactions.sql").read())
    conn.executescript(open("schema/plaid_accounts.sql").read())
    yield conn
    conn.close()


def test_table_exists(db: sqlite3.Connection):
    cur = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='transactions';"
    )
    assert cur.fetchone() is not None


def test_required_columns_exist(db: sqlite3.Connection):
    cur = db.execute("PRAGMA table_info(transactions);")
    columns = {row[1]: row for row in cur.fetchall()}

    for col in ["id", "name", "amount", "direction", "occurred_at", "note"]:
        assert col in columns


def test_not_null_constraints(db: sqlite3.Connection):
    cur = db.execute("PRAGMA table_info(transactions);")
    columns = {row[1]: row for row in cur.fetchall()}

    assert columns["name"][3] == 1
    assert columns["amount"][3] == 1
    assert columns["direction"][3] == 1
    assert columns["occurred_at"][3] == 1


def test_direction_enum_invalid(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ("Test Account", "ext-a", "APPLE", "DEPOSITORY"),
    )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO transactions (name, amount, direction, account_id)
            VALUES ('bad', 100, 'sideways', 1);
            """
        )


def test_direction_enum_valid(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ("Test Account", "ext-a", "APPLE", "DEPOSITORY"),
    )

    db.execute(
        """
        INSERT INTO transactions (name, amount, direction, account_id)
        VALUES ('salary', 500000, 'IN', 1);
        """
    )

    db.execute(
        """
        INSERT INTO transactions (name, amount, direction, account_id)
        VALUES ('groceries', 3500, 'OUT', 1);
        """
    )


def test_default_occurred_at(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ("Test Account", "ext-a", "APPLE", "DEPOSITORY"),
    )

    db.execute(
        """
        INSERT INTO transactions (name, amount, direction, account_id)
        VALUES ('coffee', 400, 'OUT', 1);
        """
    )
    db.commit()

    cur = db.execute("SELECT occurred_at FROM transactions;")
    occurred_at = cur.fetchone()[0]
    assert occurred_at is not None


def test_autoincrement_id(db):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ("Test Account", "ext-a", "APPLE", "DEPOSITORY"),
    )

    db.execute(
        "INSERT INTO transactions (name, amount, direction, account_id) VALUES ('A', 23, 'IN', 1);"
    )
    db.execute(
        "INSERT INTO transactions (name, amount, direction, account_id) VALUES ('B', 24, 'OUT', 1);"
    )

    ids = [
        r[0] for r in db.execute("SELECT id FROM transactions ORDER BY id;")
    ]
    assert ids == [1, 2]

def test_external_id_unique_dup_dropped(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO accounts (name, external_id, source, account_type) VALUES (?,?,?,?)",
        ("Test Account", "ext-a", "APPLE", "DEPOSITORY"),
    )

    db.execute(
        """
        INSERT INTO transactions (name, amount, direction, external_id, account_id)
        VALUES ('txn1', 1000, 'IN', 'ext-123', 1);
        """
    )

    db.execute(
        """
        INSERT INTO transactions (name, amount, direction, external_id, account_id)
        VALUES ('txn2', 2000, 'OUT', 'ext-123', 1);
        """
    )