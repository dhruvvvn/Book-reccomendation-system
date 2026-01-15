"""Models package initialization - exports all Pydantic schemas."""

from app.models.book import BookBase, BookInDB, BookResponse, BookFilters
from app.models.chat import ChatRequest, ChatResponse
from app.models.recommendation import RecommendationCandidate, RecommendationResult

__all__ = [
    "BookBase",
    "BookInDB", 
    "BookResponse",
    "BookFilters",
    "ChatRequest",
    "ChatResponse",
    "RecommendationCandidate",
    "RecommendationResult",
]
