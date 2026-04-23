import os
import sys
import mysql.connector

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import DB_CONFIG

def update_db():
    print("Updating database schema...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Check if column exists first (more compatible than IF NOT EXISTS)
        cur.execute("SHOW COLUMNS FROM users LIKE 'profile_pic'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE users ADD COLUMN profile_pic VARCHAR(255) DEFAULT NULL")
            conn.commit()
            print("✅ Database updated: 'profile_pic' column added.")
        else:
            print("ℹ️ Column 'profile_pic' already exists.")
        
        # Create upload directory
        upload_path = os.path.join('static', 'uploads', 'profiles')
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
            print(f"✅ Folder created: {upload_path}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cur.close()
            conn.close()

if __name__ == "__main__":
    update_db()
