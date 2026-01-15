"""
Enhanced CSV to JSON Converter with Genre Detection

Improved version that:
- Processes all books (or specified limit)
- Detects genres from title/publisher keywords
- Assigns random ratings for demo purposes
- Creates richer descriptions
"""

import csv
import json
import random
from pathlib import Path
from typing import List, Dict, Any

INPUT_FILE = Path(r"c:\Users\HP\Desktop\Book reccomendation sys\books.csv")
OUTPUT_FILE = Path(r"c:\Users\HP\Desktop\Book reccomendation sys\backend\data\books_kaggle.json")

# Genre detection keywords
GENRE_KEYWORDS = {
    "Romance": ["love", "heart", "romance", "kiss", "wedding", "bride", "passion", "desire", "harlequin"],
    "Mystery": ["mystery", "detective", "murder", "crime", "thriller", "suspense", "investigation", "clue"],
    "Science Fiction": ["space", "alien", "galaxy", "robot", "future", "sci-fi", "mars", "planet", "star trek", "star wars"],
    "Fantasy": ["magic", "dragon", "wizard", "witch", "kingdom", "sword", "quest", "lord", "fairy", "enchant"],
    "Horror": ["horror", "ghost", "vampire", "zombie", "haunted", "terror", "nightmare", "fear", "dark"],
    "Action": ["action", "adventure", "hero", "warrior", "battle", "fight", "mission", "escape"],
    "Historical": ["history", "historical", "war", "century", "ancient", "medieval", "revolution", "civil war"],
    "Biography": ["biography", "memoir", "life", "autobiography", "story of", "years of"],
    "Self-Help": ["self-help", "success", "habits", "mindset", "motivation", "guide to", "how to"],
    "Children": ["children", "kids", "young", "boy", "girl", "adventures of", "tales", "bedtime"],
    "Cooking": ["cookbook", "recipes", "cooking", "kitchen", "food", "baking", "chef"],
    "Religion": ["bible", "god", "faith", "christian", "prayer", "spiritual", "church", "jesus"],
}

def detect_genre(title: str, publisher: str) -> str:
    """Detect genre from title and publisher keywords."""
    text = f"{title} {publisher}".lower()
    
    for genre, keywords in GENRE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return genre
    
    return "Fiction"  # Default genre

def generate_rating() -> float:
    """Generate realistic-looking rating (mostly 3-4.5 range)."""
    # Weighted towards middle-high ratings
    base = random.gauss(3.8, 0.7)
    return round(max(1.0, min(5.0, base)), 1)

def create_description(title: str, author: str, publisher: str, year: str, genre: str) -> str:
    """Create a richer description for semantic search."""
    templates = [
        f"{title} by {author} is a captivating {genre.lower()} published by {publisher} in {year}.",
        f"Published in {year}, {title} is a {genre.lower()} work by {author} from {publisher}.",
        f"This {genre.lower()} book by {author}, {title}, was released by {publisher} in {year}.",
    ]
    return random.choice(templates)

def convert_csv_to_json(limit: int = 5000):
    print(f"Reading from {INPUT_FILE}...")
    print(f"Processing up to {limit} books")
    
    books = []
    encodings = ['utf-8-sig', 'cp1252', 'latin-1']
    
    success = False
    rows_processed = 0
    
    for enc in encodings:
        print(f"Trying encoding: {enc}...")
        try:
            with open(INPUT_FILE, 'r', encoding=enc, errors='replace') as f:
                reader = csv.DictReader(f, delimiter=';', quotechar='"')
                
                headers = reader.fieldnames
                if not headers or "Book-Title" not in headers:
                    print(f"Headers look wrong with {enc}: {headers}")
                    continue
                
                print(f"Valid headers found. Processing...")
                
                for row in reader:
                    title = row.get("Book-Title", "").strip()
                    author = row.get("Book-Author", "").strip()
                    publisher = row.get("Publisher", "").strip()
                    year = row.get("Year-Of-Publication", "").strip()
                    cover = row.get("Image-URL-L", "").strip()
                    
                    # Skip invalid entries
                    if not title or not author or len(title) < 2:
                        continue
                    
                    # Detect genre
                    genre = detect_genre(title, publisher)
                    
                    # Generate realistic rating
                    rating = generate_rating()
                    
                    # Create rich description
                    description = create_description(title, author, publisher, year, genre)
                    
                    book = {
                        "title": title,
                        "author": author,
                        "description": description,
                        "genre": genre,
                        "rating": rating,
                        "cover_url": cover if cover.startswith("http") else None,
                        "year": year
                    }
                    books.append(book)
                    rows_processed += 1
                    
                    if rows_processed % 1000 == 0:
                        print(f"  Processed {rows_processed} books...")
                    
                    if rows_processed >= limit:
                        print(f"Reached limit of {limit} books.")
                        break
                
                success = True
                break
                
        except Exception as e:
            print(f"Failed with {enc}: {e}")
            continue
    
    if not success:
        print("CRITICAL: Could not read file with any encoding.")
        return
    
    # Show genre distribution
    print("Genre Distribution:")
    genre_counts = {}
    for book in books:
        genre = book["genre"]
        genre_counts[genre] = genre_counts.get(genre, 0) + 1
    
    for genre, count in sorted(genre_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"   {genre}: {count} books")
    
    # Save to JSON
    print(f"Saving to {OUTPUT_FILE}...")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(books, f, indent=2, ensure_ascii=False)
    
    print(f"Done! Converted {rows_processed} books.")
    print(f"Output: {OUTPUT_FILE}")

if __name__ == "__main__":
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    convert_csv_to_json(limit)
