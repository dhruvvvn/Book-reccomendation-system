"""
Download Book Covers Script

Downloads all book cover images locally to avoid external API dependencies
and broken image links.

Features:
- Polite rate limiting to avoid IP bans
- Progress bar for visual feedback
- Skips already downloaded images
- Updates the JSON data with local paths
"""

import asyncio
import aiohttp
import json
import os
from pathlib import Path
from tqdm.asyncio import tqdm
import hashlib

# Configuration
DATA_FILE = Path(r"c:\Users\HP\Desktop\Book reccomendation sys\backend\data\books_enriched.json")
COVERS_DIR = Path(r"c:\Users\HP\Desktop\Book reccomendation sys\backend\app\static\covers")
OUTPUT_FILE = Path(r"c:\Users\HP\Desktop\Book reccomendation sys\backend\data\books_local_covers.json")

# Rate limiting - be polite to servers
CONCURRENCY_LIMIT = 10  # Simultaneous downloads
RATE_LIMIT_DELAY = 0.1  # Seconds between batches

# Stats
stats = {"downloaded": 0, "skipped": 0, "failed": 0, "already_local": 0}


def get_safe_filename(book_id: str, url: str) -> str:
    """Generate a safe filename for the cover image."""
    # Use book ID + hash of URL for uniqueness
    ext = ".jpg"  # Default extension
    if ".png" in url.lower():
        ext = ".png"
    elif ".gif" in url.lower():
        ext = ".gif"
    
    return f"{book_id}{ext}"


async def download_cover(session: aiohttp.ClientSession, book: dict, semaphore: asyncio.Semaphore) -> dict:
    """Download a single book cover."""
    global stats
    
    book_id = str(book.get("id", hash(book["title"])))
    cover_url = book.get("cover_url", "")
    
    # Skip if no cover URL
    if not cover_url:
        stats["skipped"] += 1
        return book
    
    # Skip if already a local path
    if cover_url.startswith("/covers/") or cover_url.startswith("covers/"):
        stats["already_local"] += 1
        return book
    
    # Generate filename
    filename = get_safe_filename(book_id, cover_url)
    filepath = COVERS_DIR / filename
    
    # Skip if already downloaded
    if filepath.exists():
        book["cover_url"] = f"/covers/{filename}"
        stats["skipped"] += 1
        return book
    
    async with semaphore:
        try:
            # Add small delay for politeness
            await asyncio.sleep(RATE_LIMIT_DELAY)
            
            async with session.get(cover_url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Save to file
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    
                    # Update book to use local path
                    book["cover_url"] = f"/covers/{filename}"
                    stats["downloaded"] += 1
                else:
                    stats["failed"] += 1
                    
        except Exception as e:
            stats["failed"] += 1
    
    return book


async def main():
    print("=" * 50)
    print("Book Cover Downloader")
    print("=" * 50)
    
    # Create covers directory
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Saving covers to: {COVERS_DIR}")
    
    # Load books
    if not DATA_FILE.exists():
        print(f"Error: Data file not found: {DATA_FILE}")
        return
    
    print(f"Loading books from: {DATA_FILE}")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        books = json.load(f)
    
    print(f"Found {len(books)} books to process")
    
    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    # Create HTTP session with headers to look like a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    }
    
    connector = aiohttp.TCPConnector(limit=CONCURRENCY_LIMIT, force_close=True)
    
    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
        # Create tasks
        tasks = [download_cover(session, book, semaphore) for book in books]
        
        # Process with progress bar
        print("\nDownloading covers...")
        updated_books = []
        for coro in tqdm.as_completed(tasks, total=len(tasks), desc="Progress"):
            result = await coro
            updated_books.append(result)
    
    # Save updated books with local paths
    print(f"\nSaving updated data to: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(updated_books, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"  Downloaded:      {stats['downloaded']}")
    print(f"  Already cached:  {stats['skipped']}")
    print(f"  Already local:   {stats['already_local']}")
    print(f"  Failed:          {stats['failed']}")
    print("=" * 50)
    
    # Calculate approximate size
    total_size = sum(f.stat().st_size for f in COVERS_DIR.glob("*") if f.is_file())
    print(f"Total disk usage: {total_size / (1024*1024):.2f} MB")
    print("\nDone! Now update your ingest script to use 'books_local_covers.json'")


if __name__ == "__main__":
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
