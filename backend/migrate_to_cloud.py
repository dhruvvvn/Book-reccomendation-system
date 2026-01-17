import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
LOCAL_DB_PATH = "backend/data/bookai.db"
# PASTE YOUR RENDER EXTERNAL DATABASE URL HERE
# It looks like: postgres://user:password@host.render.com/db_name
CLOUD_DB_URL = os.getenv("CLOUD_DB_URL") 

def migrate():
    if not CLOUD_DB_URL:
        logger.error("Please set CLOUD_DB_URL environment variable or hardcode it in the script.")
        return

    print(f"Connecting to Cloud DB...")
    try:
        pg_conn = psycopg2.connect(CLOUD_DB_URL)
        pg_cursor = pg_conn.cursor()
        print("Connected to Cloud DB successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to Cloud DB: {e}")
        return

    # 1. Create Tables (Idempotent)
    print("\n--- Creating Tables ---")
    try:
        # Users
        pg_cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                theme TEXT DEFAULT 'dark',
                personality TEXT DEFAULT 'friendly',
                favorite_genres TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Books
        pg_cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                description TEXT,
                genre TEXT,
                rating REAL,
                cover_url TEXT,
                source TEXT DEFAULT 'local',
                year_published INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Reading List
        pg_cursor.execute("""
            CREATE TABLE IF NOT EXISTS reading_list (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                book_id TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, book_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        # Other tables just in case (optional for migration but good for app)
        pg_cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        pg_conn.commit()
        print("Tables created/verified.")
    except Exception as e:
        print(f"Error creating tables: {e}")
        pg_conn.rollback() # Important to rollback if failed

    # 2. Migrate Users
    print("\n--- Migrating Users ---")
    local_conn = sqlite3.connect(LOCAL_DB_PATH)
    local_cursor = local_conn.cursor()
    
    try:
        # Removed 'disabled' as it's not in SQLite schema
        local_cursor.execute("SELECT id, username, password_hash, display_name FROM users")
        users = local_cursor.fetchall()
        
        if users:
            # Postgres INSERT
            insert_query = """
                INSERT INTO users (id, username, password_hash, display_name)
                VALUES %s
                ON CONFLICT (id) DO NOTHING;
            """
            execute_values(pg_cursor, insert_query, users)
            print(f"Migrated {len(users)} users.")
        else:
            print("No users found locally.")
            
    except Exception as e:
        print(f"Error migrating users: {e}")

    # 3. Migrate Books
    print("\n--- Migrating Books ---")
    try:
        # We migrate from the 'books' table in SQLite which acts as our cache/store
        # Schema: id, title, author, description, genre, rating, cover_url, source, year_published, created_at
        local_cursor.execute("SELECT id, title, author, description, genre, rating, cover_url, source, year_published, created_at FROM books")
        books = local_cursor.fetchall()
        
        if books:
            # Postgres INSERT
            insert_query = """
                INSERT INTO books (id, title, author, description, genre, rating, cover_url, source, year_published, created_at)
                VALUES %s
                ON CONFLICT (id) DO NOTHING;
            """
            execute_values(pg_cursor, insert_query, books, page_size=100)
            print(f"Migrated {len(books)} books.")
        else:
            print("No books found in local DB.")

    except Exception as e:
        print(f"Error migrating books: {e}")

    # 3. Migrate Reading List
    print("\n--- Migrating Reading List ---")
    try:
        local_cursor.execute("SELECT id, user_id, book_id, added_at FROM reading_list")
        items = local_cursor.fetchall()
        
        if items:
            insert_query = """
                INSERT INTO reading_list (id, user_id, book_id, added_at)
                VALUES %s
                ON CONFLICT (id) DO NOTHING;
            """
            execute_values(pg_cursor, insert_query, items)
            print(f"Migrated {len(items)} reading list items.")
        else:
            print("No reading list items found.")
            
    except Exception as e:
        print(f"Error migrating reading list: {e}")

    # Commit and Close
    pg_conn.commit()
    pg_cursor.close()
    pg_conn.close()
    local_conn.close()
    print("\nMigration Complete!")

if __name__ == "__main__":
    if not os.path.exists(LOCAL_DB_PATH):
        print(f"Error: Local database {LOCAL_DB_PATH} not found.")
    else:
        migrate()
