CREATE TABLE IF NOT EXISTS
    transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        amount INTEGER NOT NULL, -- stored in cents (e.g. $12.34 = 1234)
        direction TEXT NOT NULL CHECK (direction IN ('IN', 'OUT')),
        occurred_at TEXT NOT NULL DEFAULT (datetime ('now')),
        external_id TEXT UNIQUE ON CONFLICT IGNORE,
        account_id INTEGER NOT NULL,
        note TEXT,
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
    );