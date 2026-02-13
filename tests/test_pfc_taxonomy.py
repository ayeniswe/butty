from core import pfc_taxonomy as pfc


def test_parse_categories_skips_notes_and_dedupes():
    csv_text = """PFCv2 Primary,PFCv2 Detailed
Note: header note,,
FOOD,FOOD_DINING
FOOD,FOOD_DINING
RENT,RENT_HOME
"""
    cats = pfc._parse_categories(csv_text)
    assert ("FOOD", "FOOD_DINING") in cats
    assert ("RENT", "RENT_HOME") in cats
    # duplicated detailed removed
    assert len([c for c in cats if c[1] == "FOOD_DINING"]) == 1


def test_load_pfc_taxonomy_uses_cache_when_fresh(tmp_path, monkeypatch):
    cache = tmp_path / "pfc.csv"
    cache.write_text("primary,detailed\nFOOD,FOOD_DINING\n", encoding="utf-8")

    calls = {}

    def fake_download(url):
        calls["downloaded"] = True
        return "primary,detailed\nRENT,RENT_HOME\n"

    monkeypatch.setattr(pfc, "_download_csv", fake_download)
    monkeypatch.setattr(pfc, "DEFAULT_CACHE_PATH", cache)
    monkeypatch.setattr(pfc, "DEFAULT_CACHE_TTL_DAYS", 999)

    cats = pfc.load_pfc_taxonomy(cache_path=cache, max_age_days=999)
    # Should use cache and not download
    assert "downloaded" not in calls
    assert ("FOOD", "FOOD_DINING") in cats


def test_seed_plaid_categories_handles_existing(monkeypatch, tmp_path):
    class FakeStore:
        def __init__(self):
            self.existing = [type("Cat", (), {"detailed": "OLD"})]
            self.added = []

        def retrieve_plaid_categories(self):
            return self.existing

        def upsert_plaid_category(self, primary, detailed):
            self.added.append((primary, detailed))
            return 1

    fake_csv = "primary,detailed\nNEW,NEW_CAT\nOLD,OLD\n"
    monkeypatch.setattr(pfc, "_download_csv", lambda url: fake_csv)
    cache = tmp_path / "pfc.csv"

    added = pfc.seed_plaid_categories_from_taxonomy(
        FakeStore(), max_age_days=0, cache_path=cache
    )
    assert added == 1
