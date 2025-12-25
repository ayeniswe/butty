CREATE TABLE
    IF NOT EXISTS budgets_transactions (
        transaction_id INTEGER NOT NULL,
        budget_id INTEGER NOT NULL,
        PRIMARY KEY (transaction_id, budget_id),
        FOREIGN KEY (transaction_id) REFERENCES transactions (id) ON DELETE CASCADE,
        FOREIGN KEY (budget_id) REFERENCES budgets (id) ON DELETE CASCADE
    );