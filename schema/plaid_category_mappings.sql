CREATE TABLE IF NOT EXISTS plaid_category_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    budget_id INTEGER NOT NULL,
    plaid_category_id INTEGER NOT NULL,
    FOREIGN KEY(budget_id) REFERENCES budgets(id) ON DELETE CASCADE,
    FOREIGN KEY(plaid_category_id) REFERENCES plaid_categories(id) ON DELETE CASCADE,
    UNIQUE(budget_id, plaid_category_id)
);
