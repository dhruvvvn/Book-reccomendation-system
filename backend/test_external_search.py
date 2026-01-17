"""Test script for external book search functionality."""
import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.services.external_search import get_external_search_service

async def test_external_search():
    print("=" * 50)
    print("TESTING EXTERNAL BOOK SEARCH")
    print("=" * 50)
    
    service = get_external_search_service()
    
    # Test 1: Search for a specific book not in local DB
    query = "The Way of the Superior Man"
    print(f"\nTest 1: Searching for '{query}'")
    print("-" * 40)
    
    books = await service.search(query, max_results=1)
    
    if books:
        book = books[0]
        print(f"[OK] FOUND: {book.title}")
        print(f"   Author: {book.author}")
        print(f"   Genre: {book.genre}")
        print(f"   Rating: {book.rating}")
        print(f"   Cover URL: {book.cover_url}")
        print(f"   Description: {book.description[:100]}..." if book.description else "   Description: N/A")
        print(f"   Is Dynamic: {book.is_dynamic}")
    else:
        print("[FAIL] No books found")
    
    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_external_search())
