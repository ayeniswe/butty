CREATE TABLE IF NOT EXISTS
    budgets_tags (
        tag_id INTEGER NOT NULL,
        budget_id INTEGER NOT NULL,
        PRIMARY KEY (tag_id, budget_id),
        FOREIGN KEY (tag_id) REFERENCES tags(id),
        FOREIGN KEY (budget_id) REFERENCES budgets(id) ON DELETE CASCADE
    );