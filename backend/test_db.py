"""Quick test to verify database module loads correctly."""
from app.db.database import Database, get_database

print("Testing database module...")
db = get_database()
print(f"Database type: {'PostgreSQL' if db.use_postgres else 'SQLite'}")
print("Database module loaded OK!")
