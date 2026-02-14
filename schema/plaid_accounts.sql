CREATE TABLE 
    IF NOT EXISTS plaid_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL,
        institution_id TEXT NOT NULL UNIQUE,
        cursor TEXT
    );
