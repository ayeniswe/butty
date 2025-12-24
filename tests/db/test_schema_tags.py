import sqlite3
import pytest


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(open("schema/tags.sql").read())
    yield conn
    conn.close()


def test_tags_table_exists(db: sqlite3.Connection):
    cur = db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='tags';
    """)
    assert cur.fetchone() is not None


def test_tags_columns(db: sqlite3.Connection):
    cur = db.execute("PRAGMA table_info(tags);")
    cols = {row[1] for row in cur.fetchall()}

    assert cols == {"id", "name"}


def test_name_not_null(db: sqlite3.Connection):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("""
            INSERT INTO tags (name)
            VALUES (NULL);
        """)


def test_autoincrement_id(db: sqlite3.Connection):
    db.execute("INSERT INTO tags (name) VALUES ('A');")
    db.execute("INSERT INTO tags (name) VALUES ('B');")

    ids = [r[0] for r in db.execute("SELECT id FROM tags ORDER BY id;")]
    assert ids == [1, 2]
