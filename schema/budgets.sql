CREATE TABLE IF NOT EXISTS
    budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        amount_allocated INTEGER NOT NULL DEFAULT 0, -- stored in cents (e.g. $12.34 = 1234)
        amount_spent INTEGER NOT NULL DEFAULT 0, -- stored in cents (e.g. $12.34 = 1234)
        amount_saved INTEGER NOT NULL DEFAULT 0, -- stored in cents (e.g. $12.34 = 1234)
        created_at TEXT NOT NULL DEFAULT (datetime ('now')),
        level TEXT CHECK (level IN ('LOW', 'MED', 'HIGH'))
    );

CREATE TRIGGER IF NOT EXISTS budgets_amount_saved
UPDATE ON budgets BEGIN
UPDATE budgets
SET
    amount_saved = NEW.amount_allocated - NEW.amount_spent
WHERE
    id = NEW.id;

END;