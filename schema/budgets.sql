CREATE TABLE IF NOT EXISTS
    budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        amount_allocated REAL NOT NULL DEFAULT 0,
        amount_spent REAL NOT NULL DEFAULT 0,
        amount_saved REAL NOT NULL DEFAULT 0,
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