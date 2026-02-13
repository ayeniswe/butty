ALTER TABLE transactions
ADD COLUMN plaid_category_id INTEGER REFERENCES plaid_categories(id);
