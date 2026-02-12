import sqlite3

import pytest


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(open("schema/budgets.sql").read())
    conn.executescript(open("schema/plaid_categories.sql").read())
    conn.executescript(open("schema/plaid_category_mappings.sql").read())
    yield conn
    conn.close()


def test_tables_exist(db: sqlite3.Connection):
    categories = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='plaid_categories';"
    ).fetchone()
    mappings = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='plaid_category_mappings';"
    ).fetchone()

    assert categories is not None
    assert mappings is not None


def test_plaid_mapping_requires_existing_budget_and_category(db: sqlite3.Connection):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO plaid_category_mappings (budget_id, plaid_category_id) VALUES (1, 1);"
        )


def test_plaid_category_can_only_map_once(db: sqlite3.Connection):
    db.execute(
        "INSERT INTO budgets (name, amount_allocated) VALUES ('Coffee', 1000);"
    )
    db.execute(
        "INSERT INTO budgets (name, amount_allocated) VALUES ('Cafe', 1000);"
    )
    db.execute(
        "INSERT INTO plaid_categories (\"primary\", detailed) VALUES ('FOOD_AND_DRINK', 'FOOD_AND_DRINK_COFFEE');"
    )

    db.execute(
        "INSERT INTO plaid_category_mappings (budget_id, plaid_category_id) VALUES (1, 1);"
    )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO plaid_category_mappings (budget_id, plaid_category_id) VALUES (2, 1);"
        )
