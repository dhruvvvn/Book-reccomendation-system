"""
Kindle Dataset Ingestion Script
================================
Converts kindle_data-v2.csv to our JSON format for the book recommendation system.

Output Schema:
{
    "id": "asin_string",
    "title": "Book Title",
    "author": "Author Name",
    "genre": "Category Name",
    "cover_url": "https://...",
    "rating": 4.5,
    "description": null  # Will be filled JIT by Gemini
}
"""

import csv
import json
import os
from pathlib import Path


def ingest_kindle_data(
    input_csv: str,
    output_json: str,
    max_books: int = None,
    min_rating: float = 3.5
):
    """
    Parse Kindle CSV and convert to JSON format.
    
    Args:
        input_csv: Path to kindle_data-v2.csv
        output_json: Path to output JSON file
        max_books: Optional limit on number of books to process
        min_rating: Minimum star rating to include (default 3.5)
    """
    books = []
    seen_titles = set()  # Deduplicate by title
    
    print(f"Reading from: {input_csv}")
    
    with open(input_csv, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader):
            if max_books and len(books) >= max_books:
                break
            
            # Skip low-rated books
            try:
                rating = float(row.get('stars', 0) or 0)
            except (ValueError, TypeError):
                rating = 0
            
            if rating < min_rating:
                continue
            
            # Skip duplicates
            title = row.get('title', '').strip()
            if not title or title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            
            # Build book object
            book = {
                "id": row.get('asin', f'kindle_{i}'),
                "title": title,
                "author": row.get('author', 'Unknown Author').strip(),
                "genre": row.get('category_name', 'General').strip(),
                "cover_url": row.get('imgUrl', '').strip(),
                "rating": round(rating, 1),
                "description": None,  # JIT filled by Gemini
                "year_published": _extract_year(row.get('publishedDate', '')),
                "is_kindle_unlimited": row.get('isKindleUnlimited', 'False') == 'True',
                "is_bestseller": row.get('isBestSeller', 'False') == 'True',
                "price": _parse_price(row.get('price', '0'))
            }
            
            books.append(book)
            
            # Progress indicator
            if len(books) % 5000 == 0:
                print(f"  Processed {len(books)} books...")
    
    print(f"Total books processed: {len(books)}")
    
    # Write output
    output_path = Path(output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(books, f, indent=2, ensure_ascii=False)
    
    print(f"Written to: {output_json}")
    
    # Print genre distribution
    genres = {}
    for book in books:
        g = book['genre']
        genres[g] = genres.get(g, 0) + 1
    
    print("\nGenre Distribution (Top 10):")
    for genre, count in sorted(genres.items(), key=lambda x: -x[1])[:10]:
        print(f"  {genre}: {count}")
    
    return len(books)


def _extract_year(date_str: str) -> int:
    """Extract year from date string like '2022-01-15'"""
    if not date_str:
        return None
    try:
        return int(date_str.split('-')[0])
    except (ValueError, IndexError):
        return None


def _parse_price(price_str: str) -> float:
    """Parse price string to float"""
    try:
        return float(price_str.replace('$', '').replace(',', '').strip() or 0)
    except (ValueError, TypeError):
        return 0.0


if __name__ == "__main__":
    # Paths
    project_root = Path(__file__).parent.parent.parent  # Go up to project root
    csv_path = project_root / "kindle_data-v2.csv"
    json_path = project_root / "backend" / "data" / "books_kindle.json"
    
    print("=" * 50)
    print("KINDLE DATASET INGESTION")
    print("=" * 50)
    
    if not csv_path.exists():
        print(f"ERROR: CSV not found at {csv_path}")
        exit(1)
    
    # Process with reasonable defaults
    # Set max_books to None to process ALL books
    count = ingest_kindle_data(
        input_csv=str(csv_path),
        output_json=str(json_path),
        max_books=50000,  # Start with 50k, adjust if needed
        min_rating=3.5
    )
    
    print(f"\nSuccess! Ingested {count} books.")
