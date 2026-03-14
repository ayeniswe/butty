import datetime
from pathlib import Path

from core.datastore.db import Sqlite3


def test_plaid_category_crud(tmp_path: Path):
    db = Sqlite3(tmp_path / "test.sqlite")

    # Seed a budget
    db.insert_budget("Food", 100, override_create_date=datetime.datetime(2024, 1, 1))

    # Upsert category twice returns same id
    cat_id1 = db.upsert_plaid_category("FOOD", "FOOD_RESTAURANT")
    cat_id2 = db.upsert_plaid_category("FOOD", "FOOD_RESTAURANT")
    assert cat_id1 == cat_id2

    # Retrieve categories
    cats = db.retrieve_plaid_categories()
    assert any(c.detailed == "FOOD_RESTAURANT" for c in cats)

    # Map budget to category
    db.replace_budget_plaid_category_mappings(1, [cat_id1])
    mappings = db.retrieve_budget_plaid_category_mappings(1)
    assert mappings and mappings[0].plaid_category_id == cat_id1

    # Lookups by detailed, primary, and id
    assert db.select_budget_id_by_plaid_category("FOOD_RESTAURANT") == 1
    assert db.select_budget_id_by_plaid_category("FOOD") == 1
    assert db.select_budget_id_by_plaid_category_id(cat_id1) == 1


def test_plaid_category_lookup_prefers_latest_budget_month(tmp_path: Path):
    db = Sqlite3(tmp_path / "test.sqlite")

    db.insert_budget("Food - Feb", 100, override_create_date=datetime.datetime(2024, 2, 1))
    db.insert_budget("Food - Mar", 100, override_create_date=datetime.datetime(2024, 3, 1))

    cat_id = db.upsert_plaid_category("FOOD", "FOOD_RESTAURANT")
    db.replace_budget_plaid_category_mappings(1, [cat_id])
    db.replace_budget_plaid_category_mappings(2, [cat_id])

    assert db.select_budget_ids_by_plaid_category("FOOD_RESTAURANT") == [2, 1]
    assert db.select_budget_id_by_plaid_category("FOOD_RESTAURANT") == 2
    assert db.select_budget_ids_by_plaid_category_id(cat_id) == [2, 1]
    assert db.select_budget_id_by_plaid_category_id(cat_id) == 2
