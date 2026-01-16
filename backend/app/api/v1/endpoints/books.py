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


@router.post("/{book_id}/enrich")
async def enrich_book_cover(
    request: Request,
    book_id: str
):
    """
    JIT Enrichment: Fetch cover from Google Books if missing.
    """
    import aiohttp # Keep local to avoid circular import issues if any, but it's safe here
    import logging
    
    # Configure logging to file for debugging
    logging.basicConfig(filename='jit_debug.log', level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        vector_store = request.app.state.vector_store
        
        # 1. Find book in memory
        book = None
        book_idx = -1
        
        # logger.info(f"Looking for book {book_id}")
        
        for i, b in enumerate(vector_store.metadata):
            if str(b.id) == str(book_id):
                book = b
                book_idx = i
                break
                
        if not book:
            logger.error(f"Book {book_id} not found")
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Book not found")
            
        # 2. If already has good cover, return it
        if book.cover_url and "books.google.com" in book.cover_url:
            return {"cover_url": book.cover_url, "status": "already_enriched"}

        # 3. Fetch from Google Books
        logger.info(f"Fetching from Google Books for: {book.title}")
        
        async with aiohttp.ClientSession() as session:
            query = f"intitle:{book.title} inauthor:{book.author}"
            url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if "items" in data and len(data["items"]) > 0:
                        vol = data["items"][0]["volumeInfo"]
                        images = vol.get("imageLinks", {})
                        
                        # Get best available image
                        cover = (images.get("extraLarge") or 
                                 images.get("large") or 
                                 images.get("medium") or 
                                 images.get("thumbnail"))
                                 
                        if cover:
                            new_url = cover.replace("http://", "https://")
                            
                            # 4. Update in-memory store
                            # Pydantic v2 safe update
                            book.cover_url = new_url
                            
                            # Verify update worked
                            # logger.info(f"Updated cover to {new_url}")
                            
                            vector_store.metadata[book_idx] = book
                            
                            return {"cover_url": new_url, "status": "updated"}
                else:
                    logger.error(f"Google API error: {response.status}")
                            
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        logger.error(f"JIT Error: {error_msg}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")
            
    return {"cover_url": book.cover_url, "status": "failed"}
