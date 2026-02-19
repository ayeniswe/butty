ALTER TABLE accounts ADD COLUMN display_name TEXT;

CREATE TABLE IF NOT EXISTS ignored_plaid_categories (
    plaid_category_id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (plaid_category_id) REFERENCES plaid_categories(id) ON DELETE CASCADE
);
