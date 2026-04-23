-- ─────────────────────────────────────────────
--  Finance Dashboard — MySQL Schema
-- ─────────────────────────────────────────────

CREATE DATABASE IF NOT EXISTS finance_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE finance_db;

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(100)        NOT NULL,
  email         VARCHAR(150)        NOT NULL UNIQUE,
  password_hash VARCHAR(256)        NOT NULL,
  is_verified   TINYINT(1)          DEFAULT 0,
  wallet_balance DECIMAL(10,2)      NOT NULL DEFAULT 0.00,
  currency_code VARCHAR(10)         NOT NULL DEFAULT 'USD',
  created_at    DATETIME            DEFAULT CURRENT_TIMESTAMP
);

-- Email verification tokens
CREATE TABLE IF NOT EXISTS email_tokens (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT          NOT NULL,
  token      VARCHAR(64)  NOT NULL UNIQUE,
  token_type ENUM('verify','reset') DEFAULT 'verify',
  expires_at DATETIME     NOT NULL,
  used       TINYINT(1)   DEFAULT 0,
  created_at DATETIME     DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Expenses table (linked to user)
CREATE TABLE IF NOT EXISTS expenses (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT            NOT NULL,
  title        VARCHAR(150)   NOT NULL,
  amount       DECIMAL(10,2)  NOT NULL,
  category     VARCHAR(50)    NOT NULL,
  expense_date DATE           NOT NULL,
  note         TEXT,
  created_at   DATETIME       DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX idx_expenses_user_date ON expenses(user_id, expense_date);
CREATE INDEX idx_expenses_category  ON expenses(user_id, category);
CREATE INDEX idx_tokens_token       ON email_tokens(token);
