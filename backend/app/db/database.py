"""
SQLite Database Connection and Schema

Provides async-compatible SQLite database for:
- User accounts (username, password hash)
- User preferences (theme, personality, favorite genres)
- Chat history (messages, timestamps)
- Book interactions (reads, likes, searches)
"""

import sqlite3
import hashlib
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.config import get_settings


class Database:
    """SQLite database manager with user and interaction storage."""
    
    def __init__(self):
        settings = get_settings()
        db_path = Path(settings.faiss_index_path).parent / "bookai.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_path)
        self._init_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_tables(self):
        """Initialize database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Users table
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
        
        # Chat history table
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
        
        # User insights (what the AI learns about the user)
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
        
        # Book interactions (reads, likes, searches)
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
        
        conn.commit()
        conn.close()
    
    # ============ USER METHODS ============
    
    def _hash_password(self, password: str) -> str:
        """Hash password with SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, username: str, password: str, display_name: str = None) -> Optional[int]:
        """Create a new user. Returns user_id or None if username exists."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
                (username.lower(), self._hash_password(password), display_name or username)
            )
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            conn.close()
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user. Returns user dict or None."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password_hash = ?",
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
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def update_user_preferences(self, user_id: int, theme: str = None, 
                                 personality: str = None, favorite_genres: List[str] = None):
        """Update user preferences."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if theme:
            updates.append("theme = ?")
            values.append(theme)
        if personality:
            updates.append("personality = ?")
            values.append(personality)
        if favorite_genres is not None:
            updates.append("favorite_genres = ?")
            values.append(json.dumps(favorite_genres))
        
        if updates:
            values.append(user_id)
            cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", values)
            conn.commit()
        
        conn.close()
    
    # ============ CHAT HISTORY METHODS ============
    
    def add_chat_message(self, user_id: int, role: str, message: str):
        """Add a chat message to history."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (user_id, role, message) VALUES (?, ?, ?)",
            (user_id, role, message)
        )
        conn.commit()
        conn.close()
    
    def get_chat_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get recent chat history for a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, message, timestamp FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in reversed(rows)]
    
    # ============ USER INSIGHTS METHODS ============
    
    def add_user_insight(self, user_id: int, insight: str, category: str = "general"):
        """Store an insight about the user learned by the AI."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_insights (user_id, insight, category) VALUES (?, ?, ?)",
            (user_id, insight, category)
        )
        conn.commit()
        conn.close()
    
    def get_user_insights(self, user_id: int) -> List[Dict]:
        """Get all insights about a user."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT insight, category, created_at FROM user_insights WHERE user_id = ?",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # ============ INTERACTION METHODS ============
    
    def log_interaction(self, user_id: int, book_id: str, action: str):
        """Log a user interaction with a book (view, like, read, search)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO interactions (user_id, book_id, action) VALUES (?, ?, ?)",
            (user_id, book_id, action)
        )
        conn.commit()
        conn.close()
    
    def get_user_interactions(self, user_id: int, action: str = None, limit: int = 50) -> List[Dict]:
        """Get user's book interactions."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if action:
            cursor.execute(
                "SELECT book_id, action, timestamp FROM interactions WHERE user_id = ? AND action = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, action, limit)
            )
        else:
            cursor.execute(
                "SELECT book_id, action, timestamp FROM interactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit)
            )
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]


# Singleton instance
_db_instance: Optional[Database] = None

def get_database() -> Database:
    """Get or create database singleton."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
