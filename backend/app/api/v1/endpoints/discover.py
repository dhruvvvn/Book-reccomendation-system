"""
Discover Endpoint

Provides homepage data for Netflix-style browsing:
- Hero section with featured book
- Genre-based carousels (Trending, Romance, Action, etc.)
"""

import random
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, Query

from app.models.book import BookInDB

router = APIRouter()


def _book_to_dict(book: BookInDB) -> Dict[str, Any]:
    """Convert BookInDB to dictionary for JSON response."""
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "description": book.description,
        "genre": book.genre,
        "rating": book.rating,
        "cover_url": book.cover_url
    }


def _get_books_by_genre(books: Dict[int, BookInDB], genre: str, limit: int = 20) -> List[Dict]:
    """Filter books by genre (case-insensitive partial match)."""
    genre_lower = genre.lower()
    matching = [
        b for b in books.values() 
        if genre_lower in b.genre.lower()
    ]
    # Sort by rating descending
    matching.sort(key=lambda x: x.rating, reverse=True)
    return [_book_to_dict(b) for b in matching[:limit]]


def _get_trending_books(books: Dict[int, BookInDB], limit: int = 20) -> List[Dict]:
    """Get highest rated books as 'trending'."""
    sorted_books = sorted(books.values(), key=lambda x: x.rating, reverse=True)
    return [_book_to_dict(b) for b in sorted_books[:limit]]


def _get_random_hero(books: Dict[int, BookInDB]) -> Optional[Dict]:
    """Get a random high-rated book for hero section."""
    high_rated = [b for b in books.values() if b.rating >= 4.0]
    if not high_rated:
        high_rated = list(books.values())
    if not high_rated:
        return None
    
    hero = random.choice(high_rated[:50])  # Pick from top 50
    return _book_to_dict(hero)


@router.get("")
async def discover(
    request: Request,
    limit: int = Query(20, ge=1, le=50, description="Books per category")
) -> Dict[str, Any]:
    """
    Get homepage discovery data.
    
    Returns:
        - hero: Featured book for hero section
        - categories: List of genre rows with books
    """
    vector_store = request.app.state.vector_store
    books = vector_store._books  # Access book mapping
    
    if not books:
        return {
            "hero": None,
            "categories": []
        }
    
    # Build category rows in specified order
    # Build category rows with Kindle-specific genres
    categories = [
        {"name": "Trending Now", "books": _get_trending_books(books, limit)},
        {"name": "Mystery & Thriller", "books": _get_books_by_genre(books, "mystery", limit)},
        {"name": "Science & Math", "books": _get_books_by_genre(books, "science", limit)},
        {"name": "Biographies", "books": _get_books_by_genre(books, "biograph", limit)},
        {"name": "Technology", "books": _get_books_by_genre(books, "technology", limit)},
        {"name": "Computers", "books": _get_books_by_genre(books, "computer", limit)},
        {"name": "Parenting", "books": _get_books_by_genre(books, "parenting", limit)},
        {"name": "Literature & Fiction", "books": _get_books_by_genre(books, "fiction", limit)},
        {"name": "Teen & Young Adult", "books": _get_books_by_genre(books, "teen", limit)},
        {"name": "Business & Money", "books": _get_books_by_genre(books, "business", limit)},
    ]
    
    # Filter out empty categories
    categories = [c for c in categories if c["books"]]
    
    # Get hero and enrich its description if needed
    hero = _get_random_hero(books)
    
    if hero and (not hero.get("description") or len(hero.get("description", "")) < 30):
        # JIT enrich hero description
        from app.services.description import get_description_service
        desc_service = get_description_service()
        try:
            desc = await desc_service.get_or_generate(
                book_id=hero["id"],
                title=hero["title"],
                author=hero["author"],
                genre=hero.get("genre", "")
            )
            hero["description"] = desc
        except Exception as e:
            print(f"[Discover] Hero description enrichment failed: {e}")
    
    return {
        "hero": hero,
        "categories": categories
    }


@router.get("/search")
async def search_discover(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=50)
) -> Dict[str, Any]:
    """
    Search books by title or author.
    
    Simple text search for the search bar (not semantic).
    """
    vector_store = request.app.state.vector_store
    books = vector_store._books
    
    q_lower = q.lower()
    
    results = [
        _book_to_dict(b) for b in books.values()
        if q_lower in b.title.lower() or q_lower in b.author.lower()
    ]
    
    # Sort by rating
    results.sort(key=lambda x: x["rating"], reverse=True)
    
    return {
        "query": q,
        "results": results[:limit]
    }


@router.get("/book/{book_id}")
async def get_book(
    request: Request,
    book_id: str
) -> Dict[str, Any]:
    """Get details for a single book by ID."""
    vector_store = request.app.state.vector_store
    
    # Try to find book by ID (string or int conversion)
    book = None
    if book_id in vector_store._books:
        book = vector_store._books[book_id]
    elif book_id.isdigit() and int(book_id) in vector_store._books:
        book = vector_store._books[int(book_id)]
        
    if not book:
        # Fallback: Search all book values for matching ID field
        for b in vector_store._books.values():
            if str(b.id) == str(book_id):
                book = b
                break
    
    from fastapi import HTTPException
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
        
    return _book_to_dict(book)
