import mysql.connector
from app import DB_CONFIG

def setup_database():
    print("Connecting to MySQL...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cur = conn.cursor()

        print("Creating 'budgets' table...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
          id INT AUTO_INCREMENT PRIMARY KEY,
          user_id INT NOT NULL,
          category VARCHAR(50) NOT NULL,
          month TINYINT NOT NULL,
          year SMALLINT NOT NULL,
          amount DECIMAL(10,2) NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY uq_budget (user_id, category, month, year),
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        print("Creating 'savings_goals' table...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS savings_goals (
          id INT AUTO_INCREMENT PRIMARY KEY,
          user_id INT NOT NULL,
          title VARCHAR(150) NOT NULL,
          target_amount DECIMAL(10,2) NOT NULL,
          saved_amount DECIMAL(10,2) DEFAULT 0.00,
          deadline DATE,
          icon VARCHAR(10) DEFAULT '🎯',
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        print("Creating 'income' table...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS income (
          id INT AUTO_INCREMENT PRIMARY KEY,
          user_id INT NOT NULL,
          title VARCHAR(150) NOT NULL,
          amount DECIMAL(10,2) NOT NULL,
          category VARCHAR(50) DEFAULT 'Salary',
          income_date DATE NOT NULL,
          note TEXT,
          is_recurring TINYINT(1) DEFAULT 0,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        print("Creating 'recurring_expenses' table...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS recurring_expenses (
          id INT AUTO_INCREMENT PRIMARY KEY,
          user_id INT NOT NULL,
          title VARCHAR(150) NOT NULL,
          amount DECIMAL(10,2) NOT NULL,
          category VARCHAR(50) NOT NULL,
          day_of_month TINYINT NOT NULL DEFAULT 1,
          note TEXT,
          is_active TINYINT(1) DEFAULT 1,
          last_applied DATE,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        conn.commit()
        print("✅ SUCCESS: All required tables have been successfully added to the database!")

    except mysql.connector.Error as err:
        print(f"❌ Database Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cur.close()
            conn.close()

if __name__ == "__main__":
    setup_database()
