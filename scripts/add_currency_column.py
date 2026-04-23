import os
import sys
import mysql.connector

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import DB_CONFIG


def update_db():
    print("Updating database schema for currency setting...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("SHOW COLUMNS FROM users LIKE 'currency_code'")
        if not cur.fetchone():
            cur.execute(
                "ALTER TABLE users ADD COLUMN currency_code VARCHAR(10) NOT NULL DEFAULT 'USD'"
            )
            conn.commit()
            print("Database updated: 'currency_code' column added.")
        else:
            print("Column 'currency_code' already exists.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if "conn" in locals() and conn.is_connected():
            cur.close()
            conn.close()


if __name__ == "__main__":
    update_db()
