CREATE TABLE 
    IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        external_id TEXT UNIQUE NOT NULL ON CONFLICT IGNORE,
        plaid_id INTEGER,
        source TEXT NOT NULL CHECK (source IN ('PLAID', 'APPLE')),
        account_type TEXT NOT NULL CHECK (account_type IN ('CREDIT', 'LOAN','INVESTMENT', 'DEPOSITORY')),
        balance INTEGER NOT NULL, -- stored in cents (e.g. $12.34 = 1234)
        last_updated_at TEXT NOT NULL DEFAULT (datetime ('now')),
        fingerprint TEXT NOT NULL UNIQUE,
        FOREIGN KEY (plaid_id) REFERENCES plaid_accounts(id) ON DELETE CASCADE
    );
    
CREATE TRIGGER IF NOT EXISTS trg_accounts_last_updated
AFTER UPDATE ON accounts
FOR EACH ROW
BEGIN
    UPDATE accounts
    SET last_updated_at = datetime('now')
    WHERE id = OLD.id;
END;