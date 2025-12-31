INSERT OR IGNORE INTO accounts (name, external_id, source, account_type) VALUES
('Chase Checking',       'acc-chase-checking', 'PLAID', 'DEPOSITORY'),
('Apple Savings',        'acc-apple-savings',  'APPLE', 'DEPOSITORY'),
('Amex Gold',            'acc-amex-gold',      'PLAID', 'CREDIT');

INSERT OR IGNORE INTO budgets (name, amount_allocated) VALUES
-- Chase Checking
('Groceries',        50000),   -- $500.00
('Dining Out',       25000),   -- $250.00
('Subscriptions',   12000),   -- $120.00
('Transportation',  15000),   -- $150.00

-- Apple Savings
('Emergency Fund', 100000),   -- $1,000.00

-- Amex Gold
('Travel',          60000),   -- $600.00
('Entertainment',  20000),   -- $200.00
-- Car Loan
('Car Payment',     45000),   -- $450.00

-- Robinhood
('Long-Term Investing', 30000); -- $300.00