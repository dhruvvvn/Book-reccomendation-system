
import asyncio
import json
import sys
import os
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.database import get_database

def migrate():
    print("Starting migration of books to SQLite...")
    
    # 1. Load JSON Data
    json_path = Path("data/books_kindle.json")
    if not json_path.exists():
        print(f"Error: {json_path} not found!")
        return

    print("Loading JSON...")
    with open(json_path, "r", encoding="utf-8") as f:
        books = json.load(f)
    
    print(f"Found {len(books)} books in JSON.")
    
    # 2. Get Database
    db = get_database()
    db.create_book_table() # Ensure table exists
    
    # 3. Migrate
    count = 0
    skipped = 0
    
    for book in books:
        # Normalize fields
        try:
            book_data = {
                "id": book.get("id") or book.get("asin", str(hash(book.get("title", "")))),
                "title": book.get("title"),
                "author": book.get("author"),
                "description": book.get("description", ""),
                "genre": book.get("genre", "General"),
                "rating": float(book.get("stars", 0.0) or 0.0),
                "cover_url": book.get("imgUrl"),
                "source": "local",
                "year_published": 0 # Default
            }
            
            if not book_data["title"]:
                skipped += 1
                continue
                
            success = db.add_book(book_data)
            if success:
                count += 1
            else:
                skipped += 1
                
            if count % 1000 == 0:
                print(f"Migrated {count}...")
                
        except Exception as e:
            # print(f"Skipping book due to error: {e}")
            skipped += 1
            
    print(f"Migration Complete!")
    print(f"Successfully added: {count}")
    print(f"Skipped/Failed: {skipped}")

if __name__ == "__main__":
    migrate()
