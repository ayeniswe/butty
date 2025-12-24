CREATE TABLE
    transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        amount INTEGER NOT NULL, -- stored in cents (e.g. $12.34 = 1234)
        direction TEXT NOT NULL CHECK (direction IN ('IN', 'OUT')),
        occurred_at TEXT NOT NULL DEFAULT (datetime ('now')),
        note TEXT
    );