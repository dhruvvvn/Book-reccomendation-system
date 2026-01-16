import sqlite3
import os

DB_PATH = "data/bookai.db"

def verify_db():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database file not found at {DB_PATH}")
        return

    print(f"[OK] Database found at {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check Users
        cursor.execute("SELECT id, username, display_name, created_at, theme, personality FROM users")
        users = cursor.fetchall()
        
        print(f"\n[INFO] Found {len(users)} users:")
        print("-" * 50)
        for user in users:
            print(f"ID: {user[0]}")
            print(f"Username: {user[1]}")
            print(f"Name: {user[2]}")
            print(f"Created: {user[3]}")
            print(f"Theme: {user[4]}")
            print(f"Personality: {user[5]}")
            print("-" * 50)

    except Exception as e:
        print(f"[ERROR] Error reading database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    verify_db()
