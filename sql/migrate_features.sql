USE finance_db;

-- ── Budget planner ──────────────────────────────
CREATE TABLE IF NOT EXISTS budgets (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT           NOT NULL,
  category   VARCHAR(50)   NOT NULL,
  month      TINYINT       NOT NULL,
  year       SMALLINT      NOT NULL,
  amount     DECIMAL(10,2) NOT NULL,
  created_at DATETIME      DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_budget (user_id, category, month, year),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ── Savings goals ──────────────────────────────
CREATE TABLE IF NOT EXISTS savings_goals (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT           NOT NULL,
  title        VARCHAR(150)  NOT NULL,
  target_amount DECIMAL(10,2) NOT NULL,
  saved_amount  DECIMAL(10,2) DEFAULT 0.00,
  deadline     DATE,
  icon         VARCHAR(10)   DEFAULT '🎯',
  created_at   DATETIME      DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ── Income tracking ────────────────────────────
CREATE TABLE IF NOT EXISTS income (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  user_id     INT           NOT NULL,
  title       VARCHAR(150)  NOT NULL,
  amount      DECIMAL(10,2) NOT NULL,
  category    VARCHAR(50)   DEFAULT 'Salary',
  income_date DATE          NOT NULL,
  note        TEXT,
  is_recurring TINYINT(1)   DEFAULT 0,
  created_at  DATETIME      DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ── Recurring expenses ──────────────────────────
CREATE TABLE IF NOT EXISTS recurring_expenses (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT           NOT NULL,
  title        VARCHAR(150)  NOT NULL,
  amount       DECIMAL(10,2) NOT NULL,
  category     VARCHAR(50)   NOT NULL,
  day_of_month TINYINT       NOT NULL DEFAULT 1,
  note         TEXT,
  is_active    TINYINT(1)    DEFAULT 1,
  last_applied DATE,
  created_at   DATETIME      DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ── Wallet balance ─────────────────────────────
-- Add wallet_balance column to users if not exists
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS wallet_balance DECIMAL(10,2) DEFAULT 0.00;

-- Add currency preference column to users if not exists
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS currency_code VARCHAR(10) NOT NULL DEFAULT 'USD';

-- ── Indexes ────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_income_user_date      ON income(user_id, income_date);
CREATE INDEX IF NOT EXISTS idx_budgets_user_month    ON budgets(user_id, month, year);
CREATE INDEX IF NOT EXISTS idx_savings_user          ON savings_goals(user_id);
CREATE INDEX IF NOT EXISTS idx_recurring_user_active ON recurring_expenses(user_id, is_active);
