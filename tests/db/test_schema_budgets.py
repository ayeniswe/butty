import sqlite3
import pytest


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(open("schema/budgets.sql").read())
    yield conn
    conn.close()


def test_budgets_table_exists(db: sqlite3.Connection):
    cur = db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='budgets';
    """)
    assert cur.fetchone() is not None


def test_budgets_columns(db: sqlite3.Connection):
    cur = db.execute("PRAGMA table_info(budgets);")
    cols = {row[1] for row in cur.fetchall()}

    assert cols == {
        "id",
        "name",
        "amount_allocated",
        "amount_spent",
        "amount_saved",
        "created_at",
        "level",
    }


def test_name_not_null(db: sqlite3.Connection):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO budgets (name)
            VALUES (NULL);
        """)


def test_defaults(db: sqlite3.Connection):
    db.execute("""
        INSERT INTO budgets (name, level)
        VALUES ('Groceries', 'LOW');
    """)

    row = db.execute("""
        SELECT amount_allocated, amount_spent, amount_saved
        FROM budgets;
    """).fetchone()

    assert row == (0.0, 0.0, 0.0)

def test_level_enum_valid(db: sqlite3.Connection):
    db.execute("""
        INSERT INTO budgets (name, level)
        VALUES ('Rent', 'HIGH');
    """)
    db.execute("""
        INSERT INTO budgets (name, level)
        VALUES ('Rent', 'LOW');
    """)
    db.execute("""
        INSERT INTO budgets (name, level)
        VALUES ('Rent', 'MED');
    """)


def test_level_enum_invalid(db: sqlite3.Connection):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO budgets (name, level)
            VALUES ('Rent', 'CRITICAL');
        """)


def test_amount_saved_trigger_on_update(db: sqlite3.Connection):
    db.execute("""
        INSERT INTO budgets (name, level, amount_allocated)
        VALUES ('Food', 'MED', 500);
    """)

    db.execute("""
        UPDATE budgets
        SET amount_spent = 200
        WHERE name = 'Food';
    """)

    saved = db.execute("""
        SELECT amount_saved FROM budgets WHERE name = 'Food';
    """).fetchone()[0]

    assert saved == 300


def test_trigger_on_amount_allocated_change(db: sqlite3.Connection):
    db.execute("""
        INSERT INTO budgets (name, level, amount_allocated, amount_spent)
        VALUES ('Car', 'HIGH', 1000, 400);
    """)

    db.execute("""
        UPDATE budgets
        SET amount_allocated = 1200
        WHERE name = 'Car';
    """)

    saved = db.execute("""
        SELECT amount_saved FROM budgets WHERE name = 'Car';
    """).fetchone()[0]

    assert saved == 800

def test_autoincrement_id(db: sqlite3.Connection):
    db.execute("INSERT INTO budgets (name, level) VALUES ('A', 'LOW');")
    db.execute("INSERT INTO budgets (name, level) VALUES ('B', 'LOW');")

    ids = [r[0] for r in db.execute("SELECT id FROM budgets ORDER BY id;")]
    assert ids == [1, 2]