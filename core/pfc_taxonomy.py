"""Utilities for loading and caching Plaid's Personal Finance Category taxonomy.

This module fetches the PFCv2 taxonomy CSV from Plaid, caches it locally, and
provides a simple helper to seed the datastore with the `primary` and `detailed`
category pairs. Network failures fall back to the cached copy when available so
the app can still start without internet access.
"""

from __future__ import annotations

import csv
import logging
import os
import urllib.request
from collections.abc import Iterable
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_TAXONOMY_URL = os.getenv(
    "PFC_TAXONOMY_URL",
    "https://plaid.com/documents/pfc-taxonomy-all.csv",
)
DEFAULT_CACHE_PATH = Path(
    os.getenv("PFC_TAXONOMY_CACHE_FILE")
    or Path.cwd() / ".cache" / "pfc-taxonomy-all.csv"
)
DEFAULT_CACHE_TTL_DAYS = int(os.getenv("PFC_TAXONOMY_CACHE_TTL_DAYS", "30"))
DOWNLOAD_TIMEOUT = int(os.getenv("PFC_TAXONOMY_TIMEOUT_SECONDS", "10"))


def _is_fresh(path: Path, max_age_days: int) -> bool:
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(days=max_age_days)


def _download_csv(url: str) -> str:
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset)


def _pick_column(fieldnames: Iterable[str], needle: str) -> str | None:
    needle_lower = needle.lower()
    for name in fieldnames:
        if needle_lower in name.lower():
            return name
    return None


def _parse_categories(csv_text: str) -> list[tuple[str, str]]:
    reader = csv.DictReader(StringIO(csv_text))
    if not reader.fieldnames:
        return []

    detailed_key = _pick_column(reader.fieldnames, "detailed")
    primary_key = _pick_column(reader.fieldnames, "primary")

    categories: list[tuple[str, str]] = []
    for row in reader:
        # Skip header notes or footers that sometimes appear in the export
        if any(
            str(val).strip().lower().startswith("note") for val in row.values() if val
        ):
            continue

        detailed = (row.get(detailed_key or "", "") or "").strip()
        primary = (row.get(primary_key or "", "") or "").strip()

        if not detailed and not primary:
            continue
        if not primary:
            primary = "UNKNOWN"

        categories.append((primary, detailed or primary))

    # Preserve order but drop duplicates by detailed value
    seen = set()
    deduped: list[tuple[str, str]] = []
    for primary, detailed in categories:
        if detailed in seen:
            continue
        seen.add(detailed)
        deduped.append((primary, detailed))

    return deduped


def load_pfc_taxonomy(
    *,
    url: str = DEFAULT_TAXONOMY_URL,
    cache_path: Path = DEFAULT_CACHE_PATH,
    max_age_days: int = DEFAULT_CACHE_TTL_DAYS,
) -> list[tuple[str, str]]:
    """Load primary/detailed category pairs from Plaid's taxonomy.

    Attempts to refresh the cache when stale; falls back to the cached file if
    the download fails. Returns an empty list when nothing can be loaded.
    """

    cache_path = Path(cache_path)
    csv_text: str | None = None

    if _is_fresh(cache_path, max_age_days):
        try:
            csv_text = cache_path.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Failed to read cached PFC taxonomy: %s", exc)

    if csv_text is None:
        try:
            csv_text = _download_csv(url)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(csv_text, encoding="utf-8")
        except Exception as exc:  # pragma: no cover - network / IO guard
            logger.warning("Could not refresh PFC taxonomy from %s: %s", url, exc)
            if cache_path.exists():
                try:
                    csv_text = cache_path.read_text(encoding="utf-8")
                except Exception as read_exc:  # pragma: no cover - defensive
                    logger.error("Fallback to cached PFC taxonomy failed: %s", read_exc)
                    return []
            else:
                return []

    return _parse_categories(csv_text)


def seed_plaid_categories_from_taxonomy(
    store,
    *,
    url: str = DEFAULT_TAXONOMY_URL,
    cache_path: Path = DEFAULT_CACHE_PATH,
    max_age_days: int = DEFAULT_CACHE_TTL_DAYS,
) -> int:
    """Upsert Plaid PFC categories into the datastore.

    Returns the number of new categories written. Existing categories are left
    untouched.
    """

    categories = load_pfc_taxonomy(
        url=url, cache_path=cache_path, max_age_days=max_age_days
    )
    if not categories:
        logger.info("No PFC taxonomy categories loaded; skipping seed.")
        return 0

    try:
        existing = {cat.detailed for cat in store.retrieve_plaid_categories()}
    except Exception:  # pragma: no cover - defensive
        existing = set()

    inserted = 0
    for primary, detailed in categories:
        if detailed in existing:
            continue
        store.upsert_plaid_category(primary, detailed)
        inserted += 1

    if inserted:
        logger.info("Seeded %s Plaid categories from taxonomy", inserted)

    return inserted
