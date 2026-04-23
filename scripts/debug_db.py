import mysql.connector
from app import DB_CONFIG

def debug_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(dictionary=True)
    
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    print("USERS:")
    for u in users:
        print(f"ID: {u['id']}, Name: {u['name']}, Wallet: {u['wallet_balance']}")
        
    cur.execute("SELECT * FROM expenses")
    expenses = cur.fetchall()
    print("\nEXPENSES:")
    for e in expenses:
        print(f"ID: {e['id']}, User: {e['user_id']}, Amount: {e['amount']}")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    debug_db()
