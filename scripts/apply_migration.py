import mysql.connector
from app import DB_CONFIG

def apply_migration():
    print(f"Connecting to {DB_CONFIG['database']}...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Add the wallet_balance column
        print("Adding 'wallet_balance' column to 'users' table...")
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN wallet_balance DECIMAL(10,2) NOT NULL DEFAULT 0.00
        """)
        
        conn.commit()
        print("✅ Migration successful! The wallet_balance column has been added.")
        
    except mysql.connector.Error as err:
        if err.errno == 1060: # Duplicate column name
            print("✅ The column 'wallet_balance' already exists. You are good to go!")
        else:
            print(f"❌ ERROR: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    apply_migration()
