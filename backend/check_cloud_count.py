import os
import psycopg2

CLOUD_DB_URL = os.getenv("CLOUD_DB_URL") 

def check():
    if not CLOUD_DB_URL:
        print("Set CLOUD_DB_URL")
        return
    try:
        conn = psycopg2.connect(CLOUD_DB_URL)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM users")
        u_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM books")
        b_count = cur.fetchone()[0]
        
        print(f"Users: {u_count}")
        print(f"Books: {b_count}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
