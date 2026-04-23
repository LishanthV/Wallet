-- Finance Dashboard Schema v2
CREATE DATABASE IF NOT EXISTS finance_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE finance_db;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100) NOT NULL,
  email VARCHAR(150) NOT NULL UNIQUE, password_hash VARCHAR(256) NOT NULL,
  is_verified TINYINT(1) DEFAULT 0, wallet_balance DECIMAL(12,2) DEFAULT 0.00,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS email_tokens (
  id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL,
  token VARCHAR(64) NOT NULL UNIQUE, token_type ENUM('verify','reset') DEFAULT 'verify',
  expires_at DATETIME NOT NULL, used TINYINT(1) DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS expenses (
  id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL,
  title VARCHAR(150) NOT NULL, amount DECIMAL(10,2) NOT NULL,
  category VARCHAR(50) NOT NULL, expense_date DATE NOT NULL,
  note TEXT, is_recurring TINYINT(1) DEFAULT 0, recurring_id INT DEFAULT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS income (
  id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL,
  title VARCHAR(150) NOT NULL, amount DECIMAL(10,2) NOT NULL,
  source VARCHAR(50) NOT NULL DEFAULT 'Salary', income_date DATE NOT NULL,
  note TEXT, is_recurring TINYINT(1) DEFAULT 0, recurring_id INT DEFAULT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS recurring_rules (
  id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL,
  title VARCHAR(150) NOT NULL, amount DECIMAL(10,2) NOT NULL,
  category VARCHAR(50) NOT NULL, rule_type ENUM('expense','income') DEFAULT 'expense',
  frequency ENUM('monthly','weekly') DEFAULT 'monthly', day_of_month TINYINT DEFAULT 1,
  next_due DATE NOT NULL, is_active TINYINT(1) DEFAULT 1, note TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS budgets (
  id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL,
  category VARCHAR(50) NOT NULL, month TINYINT NOT NULL,
  year SMALLINT NOT NULL, amount DECIMAL(10,2) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_budget (user_id, category, month, year),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS savings_goals (
  id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL,
  title VARCHAR(150) NOT NULL, target_amount DECIMAL(12,2) NOT NULL,
  saved_amount DECIMAL(12,2) DEFAULT 0.00, deadline DATE DEFAULT NULL,
  icon VARCHAR(10) DEFAULT '🎯', is_completed TINYINT(1) DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS wallet_transactions (
  id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL,
  type ENUM('credit','debit') NOT NULL, amount DECIMAL(10,2) NOT NULL,
  note VARCHAR(200), created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_exp_user_date ON expenses(user_id, expense_date);
CREATE INDEX IF NOT EXISTS idx_exp_category  ON expenses(user_id, category);
CREATE INDEX IF NOT EXISTS idx_inc_user_date ON income(user_id, income_date);
CREATE INDEX IF NOT EXISTS idx_budget_user   ON budgets(user_id, month, year);
CREATE INDEX IF NOT EXISTS idx_goals_user    ON savings_goals(user_id);
CREATE INDEX IF NOT EXISTS idx_tokens_token  ON email_tokens(token);
-- Safe migration for existing DBs
ALTER TABLE users ADD COLUMN IF NOT EXISTS wallet_balance DECIMAL(12,2) DEFAULT 0.00;
