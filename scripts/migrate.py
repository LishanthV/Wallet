"""
NexWallet — Consolidated Migration Runner
Run this script to ensure your database schema is up-to-date.
Usage: python scripts/migrate.py
"""

import sys
import os
import mysql.connector
from pathlib import Path

# Robust root path detection to allow running from any directory
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

try:
    from app import DB_CONFIG
except ImportError:
    print("❌ Error: Could not find app.py to load DB_CONFIG.")
    print("Ensure you are running this from the project environment.")
    sys.exit(1)

# List of migrations to apply (Title, SQL)
# The runner handles 'Duplicate Column' errors gracefully.
MIGRATIONS = [
    ("Add profile_pic column", 
     "ALTER TABLE users ADD COLUMN profile_pic VARCHAR(255) DEFAULT NULL"),
    
    ("Add currency_code column", 
     "ALTER TABLE users ADD COLUMN currency_code VARCHAR(10) DEFAULT 'INR'"),
    
    ("Add wallet_balance non-negative constraint", 
     "ALTER TABLE users ADD CONSTRAINT check_pos_wallet CHECK (wallet_balance >= 0)"),
    
    ("Ensure recurring_expenses has description", 
     "ALTER TABLE recurring_expenses ADD COLUMN description TEXT AFTER category"),
     
    ("Index expenses by user and date",
     "CREATE INDEX idx_user_exp_date ON expenses(user_id, expense_date)"),
]

def run_migrations():
    print(f"🚀 Starting NexWallet Database Migrations...")
    print(f"📍 Root Directory: {ROOT_DIR}\n")

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        applied_count = 0
        for title, sql in MIGRATIONS:
            print(f"Checking: {title}...", end=" ")
            try:
                cur.execute(sql)
                conn.commit()
                print("✅ Applied.")
                applied_count += 1
            except mysql.connector.Error as err:
                # 1060: Duplicate column name, 3822: Duplicate check constraint, 1061: Duplicate key name
                if err.errno in [1060, 3822, 1061]:
                    print("ℹ️ Already exists.")
                else:
                    print(f"❌ Failed: {err}")
                    # Continue with other migrations if one fails unless critical
        
        # Robust asset folder creation
        profile_path = ROOT_DIR / 'static' / 'uploads' / 'profiles'
        bill_path = ROOT_DIR / 'static' / 'uploads' / 'bills'
        
        profile_path.mkdir(parents=True, exist_ok=True)
        bill_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n🎉 Migration finished. {applied_count} new changes applied.")
        
    except mysql.connector.Error as e:
        print(f"\n❌ Database Connection Error: {e}")
        sys.exit(1)
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    run_migrations()
