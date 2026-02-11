-- Add cursor column to plaid_accounts for incremental Plaid syncs
ALTER TABLE plaid_accounts ADD COLUMN cursor TEXT;
