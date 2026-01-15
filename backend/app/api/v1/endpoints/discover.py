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
    categories = [
        {"name": "Trending Now", "books": _get_trending_books(books, limit)},
        {"name": "Romance", "books": _get_books_by_genre(books, "romance", limit)},
        {"name": "Action & Adventure", "books": _get_books_by_genre(books, "action", limit)},
        {"name": "Mystery & Thriller", "books": _get_books_by_genre(books, "mystery", limit)},
        {"name": "Science Fiction", "books": _get_books_by_genre(books, "science", limit)},
        {"name": "Fantasy", "books": _get_books_by_genre(books, "fantasy", limit)},
        {"name": "Historical", "books": _get_books_by_genre(books, "history", limit)},
        {"name": "Biography", "books": _get_books_by_genre(books, "biography", limit)},
    ]
    
    # Filter out empty categories
    categories = [c for c in categories if c["books"]]
    
    return {
        "hero": _get_random_hero(books),
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
