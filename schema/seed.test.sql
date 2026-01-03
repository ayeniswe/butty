INSERT OR IGNORE INTO accounts (name, external_id, source, balance, account_type) VALUES
('Chase Checking',        'acc-chase-checking',        'PLAID', 100000, 'DEPOSITORY'),
('Apple Savings',         'acc-apple-savings',         'APPLE',  34000, 'DEPOSITORY'),
('Amex Gold',             'acc-amex-gold',             'PLAID',   1200, 'CREDIT'),

-- Additional fake accounts
('Wells Fargo Checking',  'acc-wf-checking',           'PLAID',  72500, 'DEPOSITORY'),
('Capital One Savings',   'acc-capone-savings',        'PLAID', 150000, 'DEPOSITORY'),
('Discover Cashback',     'acc-discover-cashback',     'PLAID',   3200, 'CREDIT'),
('Chase Sapphire',        'acc-chase-sapphire',        'PLAID',   5400, 'CREDIT'),
('Car Loan',              'acc-car-loan',              'PLAID', -1250000, 'LOAN'),
('Student Loan',          'acc-student-loan',          'PLAID', -3200000, 'LOAN'),
('Robinhood Brokerage',   'acc-robinhood-brokerage',   'PLAID',  875000, 'INVESTMENT'),
('Vanguard Roth IRA',     'acc-vanguard-roth-ira',     'PLAID', 2450000, 'INVESTMENT');

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