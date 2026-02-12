CREATE TABLE IF NOT EXISTS plaid_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    "primary" TEXT NOT NULL,
    detailed TEXT NOT NULL UNIQUE,
    UNIQUE("primary", detailed)
);
