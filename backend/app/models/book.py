"""
Book Pydantic Models

Defines all book-related schemas with strict validation.
Follows the principle of having separate models for different contexts:
- Base: Core shared fields
- InDB: Database representation with internal fields
- Response: API response format (what clients see)
"""

from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class BookBase(BaseModel):
    """
    Core book fields shared across all book models.
    
    This is the foundation schema containing fields that are
    always present regardless of context.
    """
    title: str = Field(..., min_length=1, max_length=500, description="Book title")
    author: str = Field(..., min_length=1, max_length=200, description="Author name")
    description: str = Field(..., min_length=1, description="Book description/summary")
    genre: str = Field(..., description="Primary genre category")
    rating: float = Field(..., ge=0, le=5, description="Average rating (0-5)")


class BookInDB(BookBase):
    """
    Book representation as stored in the database.
    
    Extends BookBase with database-specific fields like ID and
    embedding reference. Used internally, never exposed directly to API.
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="Unique book identifier")
    embedding_id: Optional[int] = Field(
        None, 
        description="Reference to embedding index in FAISS"
    )
    cover_url: Optional[str] = Field(
        None, 
        description="URL to book cover image"
    )
    popularity_score: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Normalized popularity score for hybrid ranking"
    )


class BookResponse(BookBase):
    """
    Book data returned to API clients.
    
    Contains all fields needed for frontend rendering including
    cover image URL and optional similarity score from search.
    """
    id: str = Field(..., description="Unique book identifier")
    cover_url: Optional[str] = Field(
        None, 
        description="URL to book cover (from Google Books API)"
    )
    similarity_score: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Cosine similarity score from vector search"
    )


class BookFilters(BaseModel):
    """
    Filters for book retrieval.
    
    Used for metadata filtering during hybrid retrieval.
    All fields are optional - only apply filters when specified.
    """
    genres: Optional[List[str]] = Field(
        None, 
        description="Filter to these genres"
    )
    min_rating: Optional[float] = Field(
        None, 
        ge=0, 
        le=5, 
        description="Minimum rating threshold"
    )
    max_results: Optional[int] = Field(
        None, 
        ge=1, 
        le=100,
        description="Maximum number of results"
    )
    exclude_ids: Optional[List[str]] = Field(
        None,
        description="Book IDs to exclude (e.g., already read)"
    )
