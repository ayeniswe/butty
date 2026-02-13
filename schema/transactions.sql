-- Ensure plaid_categories exists for FK even when loaded standalone in tests
CREATE TABLE IF NOT EXISTS plaid_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    "primary" TEXT NOT NULL,
    detailed TEXT NOT NULL UNIQUE,
    UNIQUE("primary", detailed)
);

CREATE TABLE IF NOT EXISTS
    transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        amount INTEGER NOT NULL, -- stored in cents (e.g. $12.34 = 1234)
        direction TEXT NOT NULL CHECK (direction IN ('IN', 'OUT')),
        occurred_at TEXT NOT NULL DEFAULT (datetime ('now')),
        external_id TEXT UNIQUE ON CONFLICT IGNORE,
        account_id INTEGER NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        fingerprint TEXT NOT NULL UNIQUE,
        plaid_category_id INTEGER,
        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
        FOREIGN KEY (plaid_category_id) REFERENCES plaid_categories(id)
    );
