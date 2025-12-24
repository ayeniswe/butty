import sqlite3
import pytest


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(open("schema/transactions.sql").read())
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
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO transactions (name, amount, direction)
            VALUES ('bad', 100, 'sideways');
            """)


def test_direction_enum_valid(db: sqlite3.Connection):
    db.execute("""
        INSERT INTO transactions (name, amount, direction)
        VALUES ('salary', 500000, 'IN');
        """)

    db.execute("""
        INSERT INTO transactions (name, amount, direction)
        VALUES ('groceries', 3500, 'OUT');
        """)


def test_default_occurred_at(db: sqlite3.Connection):
    db.execute("""
        INSERT INTO transactions (name, amount, direction)
        VALUES ('coffee', 400, 'OUT');
        """)
    db.commit()

    cur = db.execute("SELECT occurred_at FROM transactions;")
    occurred_at = cur.fetchone()[0]
    assert occurred_at is not None


def test_autoincrement_id(db):
    db.execute("INSERT INTO transactions (name, amount, direction) VALUES ('A', 23, 'IN');")
    db.execute("INSERT INTO transactions (name, amount, direction) VALUES ('B', 24, 'OUT');")

    ids = [
        r[0] for r in db.execute("SELECT id FROM transactions ORDER BY id;")
    ]
    assert ids == [1, 2]
