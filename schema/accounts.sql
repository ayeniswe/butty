CREATE TABLE 
    IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        external_id TEXT UNIQUE NOT NULL ON CONFLICT IGNORE,
        plaid_id INTEGER,
        source TEXT NOT NULL CHECK (source IN ('PLAID', 'APPLE')),
        account_type TEXT NOT NULL CHECK (account_type IN ('CREDIT', 'LOAN','INVESTMENT', 'DEPOSITORY')),
        FOREIGN KEY (plaid_id) REFERENCES plaid_accounts(id) ON DELETE CASCADE
    );
