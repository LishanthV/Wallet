-- Run this once to add wallet balance support
USE finance_db;

ALTER TABLE users
  ADD COLUMN wallet_balance DECIMAL(10,2) NOT NULL DEFAULT 0.00
  AFTER is_verified;
