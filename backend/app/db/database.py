"""
PostgreSQL Database Connection and Schema (Cloud-Ready)

Provides PostgreSQL database for:
- User accounts (username, password hash)
- User preferences (theme, personality, favorite genres)
- Chat history (messages, timestamps)
- Book interactions (reads, likes, searches)

Uses DATABASE_URL environment variable for connection.
Falls back to SQLite for local development if DATABASE_URL is not set.
"""

import os
import hashlib
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.config import get_settings

# Try PostgreSQL first, fallback to SQLite for local dev
USE_POSTGRES = bool(os.environ.get("DATABASE_URL"))

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
    import sqlite3
    from pathlib import Path


class Database:
    """Database manager supporting both PostgreSQL (cloud) and SQLite (local)."""
    
    def __init__(self):
        self.use_postgres = USE_POSTGRES
        
        if self.use_postgres:
            self.database_url = os.environ.get("DATABASE_URL")
            # Handle Render's postgres:// vs postgresql:// format
            if self.database_url.startswith("postgres://"):
                self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)
            print(f"[Database] Using PostgreSQL")
        else:
            settings = get_settings()
            from pathlib import Path
            db_path = Path(settings.faiss_index_path).parent / "bookai.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(db_path)
            print(f"[Database] Using SQLite: {self.db_path}")
        
        self._init_tables()
    
    def _get_connection(self):
        """Get database connection."""
        if self.use_postgres:
            conn = psycopg2.connect(self.database_url)
            return conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
    
    def _get_cursor(self, conn):
        """Get cursor with appropriate row factory."""
        if self.use_postgres:
            return conn.cursor(cursor_factory=RealDictCursor)
        else:
            return conn.cursor()
    
    def _placeholder(self):
        """Get the correct placeholder for the database type."""
        return "%s" if self.use_postgres else "?"
    
    def _init_tables(self):
        """Initialize database tables."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        
        p = self._placeholder()
        
        if self.use_postgres:
            # PostgreSQL schema
            cursor.execute("""
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
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_insights (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    insight TEXT NOT NULL,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    book_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            cursor.execute("""
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
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reading_list (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    book_id TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id, book_id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_queries (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    query TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_user ON search_queries(user_id)")
            
        else:
            # SQLite schema (original)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    display_name TEXT,
                    theme TEXT DEFAULT 'dark',
                    personality TEXT DEFAULT 'friendly',
                    favorite_genres TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    insight TEXT NOT NULL,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    book_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            cursor.execute("""
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reading_list (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    book_id TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, book_id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    query TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_user ON search_queries(user_id)")
        
        conn.commit()
        conn.close()
    
    # ============ USER METHODS ============
    
    def _hash_password(self, password: str) -> str:
        """Hash password with SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, username: str, password: str, display_name: str = None) -> Optional[int]:
        """Create a new user. Returns user_id or None if username exists."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        try:
            cursor.execute(
                f"INSERT INTO users (username, password_hash, display_name) VALUES ({p}, {p}, {p}) RETURNING id" if self.use_postgres else
                f"INSERT INTO users (username, password_hash, display_name) VALUES ({p}, {p}, {p})",
                (username.lower(), self._hash_password(password), display_name or username)
            )
            conn.commit()
            
            if self.use_postgres:
                result = cursor.fetchone()
                user_id = result['id'] if result else None
            else:
                user_id = cursor.lastrowid
            
            conn.close()
            return user_id
        except Exception as e:
            print(f"[Database] Create user error: {e}")
            conn.close()
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user. Returns user dict or None."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        cursor.execute(
            f"SELECT * FROM users WHERE username = {p} AND password_hash = {p}",
            (username.lower(), self._hash_password(password))
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        cursor.execute(f"SELECT * FROM users WHERE id = {p}", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def update_user_preferences(self, user_id: int, theme: str = None, 
                                 personality: str = None, favorite_genres: List[str] = None):
        """Update user preferences."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        updates = []
        values = []
        
        if theme:
            updates.append(f"theme = {p}")
            values.append(theme)
        if personality:
            updates.append(f"personality = {p}")
            values.append(personality)
        if favorite_genres is not None:
            updates.append(f"favorite_genres = {p}")
            values.append(json.dumps(favorite_genres))
        
        if updates:
            values.append(user_id)
            cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = {p}", values)
            conn.commit()
        
        conn.close()
    
    # ============ CHAT HISTORY METHODS ============
    
    def add_chat_message(self, user_id: int, role: str, message: str):
        """Add a chat message to history."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        cursor.execute(
            f"INSERT INTO chat_history (user_id, role, message) VALUES ({p}, {p}, {p})",
            (user_id, role, message)
        )
        conn.commit()
        conn.close()
    
    def get_chat_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get recent chat history for a user."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        cursor.execute(
            f"SELECT role, message, timestamp FROM chat_history WHERE user_id = {p} ORDER BY timestamp DESC LIMIT {p}",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in reversed(rows)]
    
    # ============ READER INSIGHTS METHODS ============
    
    def add_user_insight(self, user_id: int, insight: str, category: str = "general"):
        """Store an insight about the user learned by the AI."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        cursor.execute(
            f"INSERT INTO user_insights (user_id, insight, category) VALUES ({p}, {p}, {p})",
            (user_id, insight, category)
        )
        conn.commit()
        conn.close()
    
    def get_user_insights(self, user_id: int) -> List[Dict]:
        """Get all insights about a user."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        cursor.execute(
            f"SELECT insight, category, created_at FROM user_insights WHERE user_id = {p}",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # ============ BOOK METHODS ============

    def create_book_table(self):
        """Ensure books table exists (already done in init)."""
        pass  # Tables created in _init_tables

    def add_book(self, book_data: Dict[str, Any]) -> bool:
        """Add or update a book in the persistent DB."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        try:
            if self.use_postgres:
                cursor.execute(f"""
                    INSERT INTO books (id, title, author, description, genre, rating, cover_url, source, year_published)
                    VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        author = EXCLUDED.author,
                        description = EXCLUDED.description,
                        genre = EXCLUDED.genre,
                        rating = EXCLUDED.rating,
                        cover_url = EXCLUDED.cover_url,
                        source = EXCLUDED.source,
                        year_published = EXCLUDED.year_published
                """, (
                    book_data['id'],
                    book_data['title'],
                    book_data.get('author', 'Unknown'),
                    book_data.get('description', ''),
                    book_data.get('genre', 'General'),
                    book_data.get('rating', 0.0),
                    book_data.get('cover_url'),
                    book_data.get('source', 'local'),
                    book_data.get('year_published')
                ))
            else:
                cursor.execute(f"""
                    INSERT OR REPLACE INTO books 
                    (id, title, author, description, genre, rating, cover_url, source, year_published)
                    VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
                """, (
                    book_data['id'],
                    book_data['title'],
                    book_data.get('author', 'Unknown'),
                    book_data.get('description', ''),
                    book_data.get('genre', 'General'),
                    book_data.get('rating', 0.0),
                    book_data.get('cover_url'),
                    book_data.get('source', 'local'),
                    book_data.get('year_published')
                ))
            conn.commit()
            return True
        except Exception as e:
            print(f"DB Error adding book: {e}")
            return False
        finally:
            conn.close()

    def get_book_by_title(self, title: str) -> Optional[Dict]:
        """Case-insensitive title match lookup."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        if self.use_postgres:
            cursor.execute(f"SELECT * FROM books WHERE LOWER(title) = LOWER({p})", (title,))
        else:
            cursor.execute(f"SELECT * FROM books WHERE title = {p} COLLATE NOCASE", (title,))
        
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def search_books_sql(self, query: str, limit: int = 5) -> List[Dict]:
        """Fallback SQL search using LIKE/ILIKE for title/author."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        search_term = f"%{query}%"
        
        if self.use_postgres:
            cursor.execute(f"""
                SELECT * FROM books 
                WHERE title ILIKE {p} OR author ILIKE {p}
                LIMIT {p}
            """, (search_term, search_term, limit))
        else:
            cursor.execute(f"""
                SELECT * FROM books 
                WHERE title LIKE {p} OR author LIKE {p}
                LIMIT {p}
            """, (search_term, search_term, limit))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ============ INTERACTION METHODS ============
    
    def log_interaction(self, user_id: int, book_id: str, action: str, rating: float = None):
        """Log a user interaction with a book."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        final_action = action
        if rating is not None:
            final_action = f"{action}_{rating}"
            
        cursor.execute(
            f"INSERT INTO interactions (user_id, book_id, action) VALUES ({p}, {p}, {p})",
            (user_id, book_id, final_action)
        )
        conn.commit()
        conn.close()
    
    def get_user_interactions(self, user_id: int, action: str = None, limit: int = 50) -> List[Dict]:
        """Get user's book interactions."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        if action:
            cursor.execute(
                f"SELECT book_id, action, timestamp FROM interactions WHERE user_id = {p} AND action = {p} ORDER BY timestamp DESC LIMIT {p}",
                (user_id, action, limit)
            )
        else:
            cursor.execute(
                f"SELECT book_id, action, timestamp FROM interactions WHERE user_id = {p} ORDER BY timestamp DESC LIMIT {p}",
                (user_id, limit)
            )
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_user_read_history(self, user_id: int, limit: int = 20) -> List[str]:
        """Get a list of books the user has read or rated highly."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        cursor.execute(f"""
            SELECT b.title, i.action 
            FROM interactions i
            JOIN books b ON i.book_id = b.id
            WHERE i.user_id = {p} AND (i.action LIKE 'rate_%' OR i.action = 'read')
            ORDER BY i.timestamp DESC
            LIMIT {p}
        """, (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            title = row["title"]
            action = row["action"]
            if action.startswith("rate_"):
                try:
                    rating = action.split("_")[1]
                    history.append(f"{title} (Rated {rating}/5)")
                except:
                    history.append(title)
            else:
                history.append(title)
                
        return list(set(history))

    # ============ READING LIST METHODS ============
    
    def add_to_reading_list(self, user_id: int, book_id: str) -> bool:
        """Add a book to user's reading list."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        try:
            if self.use_postgres:
                cursor.execute(
                    f"INSERT INTO reading_list (user_id, book_id) VALUES ({p}, {p}) ON CONFLICT DO NOTHING",
                    (user_id, book_id)
                )
            else:
                cursor.execute(
                    f"INSERT OR IGNORE INTO reading_list (user_id, book_id) VALUES ({p}, {p})",
                    (user_id, book_id)
                )
            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success
        except Exception as e:
            print(f"[DB] add_to_reading_list error: {e}")
            conn.close()
            return False
    
    def remove_from_reading_list(self, user_id: int, book_id: str) -> bool:
        """Remove a book from user's reading list."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        cursor.execute(
            f"DELETE FROM reading_list WHERE user_id = {p} AND book_id = {p}",
            (user_id, book_id)
        )
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    def get_reading_list(self, user_id: int) -> List[Dict]:
        """Get all books in user's reading list with full book details."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        cursor.execute(f"""
            SELECT b.*, rl.added_at 
            FROM reading_list rl
            JOIN books b ON rl.book_id = b.id
            WHERE rl.user_id = {p}
            ORDER BY rl.added_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def is_in_reading_list(self, user_id: int, book_id: str) -> bool:
        """Check if a book is in user's reading list."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        cursor.execute(
            f"SELECT 1 FROM reading_list WHERE user_id = {p} AND book_id = {p}",
            (user_id, book_id)
        )
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    # ============ SEARCH QUERY METHODS ============
    
    def log_search_query(self, user_id: int, query: str):
        """Log a user's search query for personalization."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        cursor.execute(
            f"INSERT INTO search_queries (user_id, query) VALUES ({p}, {p})",
            (user_id, query)
        )
        conn.commit()
        conn.close()
    
    def get_recent_searches(self, user_id: int, limit: int = 10) -> List[str]:
        """Get user's recent search queries."""
        conn = self._get_connection()
        cursor = self._get_cursor(conn)
        p = self._placeholder()
        
        cursor.execute(f"""
            SELECT DISTINCT query FROM search_queries 
            WHERE user_id = {p} 
            ORDER BY timestamp DESC 
            LIMIT {p}
        """, (user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [row["query"] for row in rows]


# Singleton instance
_db_instance: Optional[Database] = None

def get_database() -> Database:
    """Get or create database singleton."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
