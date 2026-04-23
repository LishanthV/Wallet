import mysql.connector
from app import DB_CONFIG

def test_connection():
    print(f"Attempting to connect to MySQL database...")
    print(f"Host: {DB_CONFIG['host']}")
    print(f"User: {DB_CONFIG['user']}")
    print(f"Database: {DB_CONFIG['database']}")
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            print("\n✅ SUCCESS! Connected to MySQL Database!")
            
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            if tables:
                print("\nFound the following tables:")
                for table in tables:
                    print(f" - {table[0]}")
            else:
                print("\n⚠️ Connection successful, but no tables found. Please make sure you ran schema.sql!")
                
            cursor.close()
            conn.close()
    except mysql.connector.Error as err:
        print(f"\n❌ ERROR: {err}")

if __name__ == "__main__":
    test_connection()
