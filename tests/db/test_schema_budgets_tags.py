import sqlite3
import pytest


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(open("schema/budgets.sql").read())
    conn.executescript(open("schema/tags.sql").read())
    conn.executescript(open("schema/budgets_tags.sql").read())
    yield conn
    conn.close()


def test_budgets_tags_table_exists(db: sqlite3.Connection):
    cur = db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='budgets_tags';
    """)
    assert cur.fetchone() is not None


def test_budgets_tags_composite_primary_key(db: sqlite3.Connection):
    # insert prerequisite rows
    db.execute("INSERT INTO budgets (name, level) VALUES ('Food', 'LOW');")
    db.execute("INSERT INTO tags (name) VALUES ('Groceries');")

    # valid insert
    db.execute("""
        INSERT INTO budgets_tags (budget_id, tag_id)
        VALUES (1, 1);
    """)

    # duplicate composite key should fail
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO budgets_tags (budget_id, tag_id)
            VALUES (1, 1);
        """)


def test_budgets_tags_foreign_key_enforced(db: sqlite3.Connection):
    # no budgets or tags exist yet
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO budgets_tags (budget_id, tag_id)
            VALUES (999, 999);
        """)


def test_budgets_tags_cascade_on_delete(db: sqlite3.Connection):
    db.execute("INSERT INTO budgets (name, level) VALUES ('Rent', 'HIGH');")
    db.execute("INSERT INTO tags (name) VALUES ('Housing');")
    db.execute("""
        INSERT INTO budgets_tags (budget_id, tag_id)
        VALUES (1, 1);
    """)

    # delete parent budget
    db.execute("DELETE FROM budgets WHERE id = 1;")

    cur = db.execute("SELECT * FROM budgets_tags;")
    assert cur.fetchall() == []
