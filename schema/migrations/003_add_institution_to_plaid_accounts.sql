ALTER TABLE plaid_accounts ADD COLUMN institution_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_plaid_accounts_institution ON plaid_accounts(institution_id);
