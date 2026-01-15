"""
Books Endpoint

Direct book retrieval and search endpoints.
Useful for browsing, searching by genre, and retrieving book details.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request

from app.models.book import BookResponse, BookFilters
from app.services.retrieval import RetrievalService, get_retrieval_service

router = APIRouter()


@router.get("", response_model=List[BookResponse])
async def list_books(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of books to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max books to return"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating")
) -> List[BookResponse]:
    """
    List books with optional filtering.
    
    This endpoint provides direct access to the book catalog
    without going through the recommendation pipeline.
    
    Args:
        skip: Pagination offset
        limit: Number of books to return
        genre: Optional genre filter
        min_rating: Optional minimum rating threshold
    
    Returns:
        List of books matching the criteria
    """
    # TODO: Implement actual book listing from PostgreSQL
    # Placeholder response
    return []


@router.get("/search")
async def search_books(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    retrieval_service: RetrievalService = Depends(get_retrieval_service)
) -> List[BookResponse]:
    """
    Semantic search for books using vector similarity.
    
    Unlike the chat endpoint, this returns raw search results
    without LLM reranking or explanation generation.
    
    Args:
        q: Search query text
        retrieval_service: Injected retrieval service
    
    Returns:
        List of semantically similar books
    """
    embedding_service = request.app.state.embedding_service
    vector_store = request.app.state.vector_store
    
    # Generate embedding for search query
    query_embedding = await embedding_service.embed_text(q)
    
    # Retrieve candidates (no reranking)
    candidates = await retrieval_service.retrieve(
        query_embedding=query_embedding,
        vector_store=vector_store
    )
    
    # Convert candidates to response format
    return [
        BookResponse(
            id=c.book.id,
            title=c.book.title,
            author=c.book.author,
            description=c.book.description,
            genre=c.book.genre,
            rating=c.book.rating,
            cover_url=c.book.cover_url,
            similarity_score=c.similarity_score
        )
        for c in candidates
    ]


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: str) -> BookResponse:
    """
    Get a specific book by ID.
    
    Args:
        book_id: Unique book identifier
    
    Returns:
        Book details
    
    Raises:
        HTTPException: If book not found
    """
    # TODO: Implement actual book retrieval from PostgreSQL
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Book not found")
