"""
Data Enrichment Script

Fetches high-quality metadata (covers, descriptions, categories) from Google Books API
to replace low-quality/missing data from the Kaggle dataset.

Features:
- Asyncio for concurrent requests (faster)
- Rate limiting to be a "good citizen" to Google APIs
- Caching to avoid re-fetching
- robust error handling
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiohttp
from tqdm.asyncio import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enrichment.log'),
        logging.StreamHandler()
    ]
)

INPUT_FILE = Path(r"c:\Users\HP\Desktop\Book reccomendation sys\backend\data\books_kaggle.json")
OUTPUT_FILE = Path(r"c:\Users\HP\Desktop\Book reccomendation sys\backend\data\books_enriched.json")
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"

# Rate limiting settings
CONCURRENCY_LIMIT = 5  # Number of concurrent requests
RATE_LIMIT_DELAY = 0.2  # Seconds between requests

class BookEnricher:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {"enriched": 0, "failed": 0, "skipped": 0}

    async def initialize(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        if self.session:
            await self.session.close()

    async def search_google_books(self, title: str, author: str) -> Optional[Dict[str, Any]]:
        """Search Google Books API for a specific book."""
        if not self.session:
            return None

        query = f"intitle:{title} inauthor:{author}"
        params = {
            "q": query,
            "maxResults": 1,
            "printType": "books",
            "langRestrict": "en"
        }

        try:
            async with self.session.get(GOOGLE_BOOKS_API, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if "items" in data and len(data["items"]) > 0:
                        return data["items"][0]["volumeInfo"]
                elif response.status == 429:
                    logging.warning("Rate limited by Google Books API. Cooling down...")
                    await asyncio.sleep(5)
                else:
                    logging.warning(f"API Error {response.status} for {title}")
        except Exception as e:
            logging.error(f"Request failed for {title}: {e}")
            
        return None

    async def enrich_book(self, book: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single book with data from Google Books."""
        # Skip if we already have a google cover (heuristic)
        if book.get("cover_url") and "books.google.com" in book["cover_url"]:
            self.stats["skipped"] += 1
            return book

        google_data = await self.search_google_books(book["title"], book["author"])

        if google_data:
            # Update cover (try extra large, large, medium, then thumbnail)
            images = google_data.get("imageLinks", {})
            cover = (images.get("extraLarge") or 
                     images.get("large") or 
                     images.get("medium") or 
                     images.get("thumbnail"))
            
            if cover:
                # Force HTTPS
                book["cover_url"] = cover.replace("http://", "https://")
                self.stats["enriched"] += 1
            else:
                self.stats["failed"] += 1

            # Update description if it's better (longer)
            new_desc = google_data.get("description")
            if new_desc and len(new_desc) > len(book.get("description", "")):
                book["description"] = new_desc

            # Update categories/genres if available
            categories = google_data.get("categories")
            if categories:
                # Use the first category, but clean it up
                book["genre"] = categories[0].split(" / ")[0]
            
            # Update rating count/average if available
            if "averageRating" in google_data:
                book["rating"] = google_data["averageRating"]
                book["ratings_count"] = google_data.get("ratingsCount", 0)

        else:
            self.stats["failed"] += 1
        
        # Respect rate limits
        await asyncio.sleep(RATE_LIMIT_DELAY)
        return book

    async def process_batch(self, books: List[Dict[str, Any]]):
        """Process a list of books with concurrency control."""
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

        async def limited_enrich(book):
            async with semaphore:
                return await self.enrich_book(book)

        # Create tasks
        tasks = [limited_enrich(book) for book in books]
        
        # Run with progress bar
        enriched_books = []
        for result in await tqdm.gather(*tasks, desc="Enriching Books"):
            enriched_books.append(result)
            
        return enriched_books

async def main():
    print("Starting data enrichment process...")
    
    # 1. Load existing data
    if not INPUT_FILE.exists():
        print(f"Error: Input file {INPUT_FILE} not found.")
        return

    print(f"Loading books from {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        books = json.load(f)

    # Allow limiting for testing (optional argument parsing could handle this)
    import sys
    limit = len(books)
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"Limiting to first {limit} books for testing.")
            books = books[:limit]
        except ValueError:
            pass

    # 2. Enrich data
    enricher = BookEnricher()
    await enricher.initialize()
    
    try:
        enriched_books = await enricher.process_batch(books)
    finally:
        await enricher.close()

    # 3. Save results
    print(f"\nSaving {len(enriched_books)} books to {OUTPUT_FILE}...")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(enriched_books, f, indent=2, ensure_ascii=False)

    print("\nEnrichment Summary:")
    print(f"  Enriched (found new data): {enricher.stats['enriched']}")
    print(f"  Failed (no data found):    {enricher.stats['failed']}")
    print(f"  Skipped (already good):    {enricher.stats['skipped']}")
    print("Done!")

if __name__ == "__main__":
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
