CREATE TABLE
    IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        plaid_id INTEGER,
        FOREIGN KEY (plaid_id) REFERENCES plaid_accounts(id) ON DELETE CASCADE
    );