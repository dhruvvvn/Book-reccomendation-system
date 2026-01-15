"""
Retrieval Service

Implements hybrid retrieval combining:
1. Vector similarity search (semantic matching via FAISS)
2. Metadata filtering (genre, rating, popularity)

Architecture Decision:
This service is the core of the Retrieve & Rerank pattern.
It returns candidates WITHOUT LLM processing - that's handled
by the reranking service.
"""

from typing import List, Optional
import numpy as np

from app.config import get_settings
from app.models.book import BookInDB, BookFilters
from app.models.recommendation import RecommendationCandidate
from app.models.chat import UserPreferences
from app.db.vector_store import VectorStore


class RetrievalService:
    """
    Service for retrieving book candidates using hybrid search.
    
    Combines vector similarity with metadata filtering to produce
    a ranked list of candidate books for LLM reranking.
    """
    
    def __init__(self):
        self._settings = get_settings()
    
    async def retrieve(
        self,
        query_embedding: np.ndarray,
        vector_store: VectorStore,
        filters: Optional[UserPreferences] = None,
        top_k: Optional[int] = None
    ) -> List[RecommendationCandidate]:
        """
        Retrieve candidate books using hybrid search.
        
        Flow:
        1. Perform vector similarity search
        2. Apply metadata filters
        3. Combine scores
        4. Return ranked candidates
        
        Args:
            query_embedding: Embedded query vector
            vector_store: FAISS vector store instance
            filters: Optional user preferences for filtering
            top_k: Number of candidates to return (default from settings)
            
        Returns:
            List of RecommendationCandidate sorted by combined score
        """
        top_k = top_k or self._settings.top_k_candidates
        
        # Step 1: Vector similarity search
        # Retrieve more than needed to allow for filtering
        search_results = await vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k * 2  # Over-fetch to account for filtering
        )
        
        # Step 2: Convert to candidates and apply filters
        candidates: List[RecommendationCandidate] = []
        
        for result in search_results:
            book = result["book"]
            similarity_score = result["score"]
            
            # Skip if below similarity threshold
            if similarity_score < self._settings.min_similarity_score:
                continue
            
            # Apply metadata filters
            if filters and not self._passes_filters(book, filters):
                continue
            
            # Calculate metadata score (rating + popularity blend)
            metadata_score = self._calculate_metadata_score(book)
            
            # Combine scores (weighted average)
            # 70% semantic, 30% metadata
            combined_score = (0.7 * similarity_score) + (0.3 * metadata_score)
            
            candidate = RecommendationCandidate(
                book=book,
                similarity_score=similarity_score,
                metadata_score=metadata_score,
                combined_score=combined_score
            )
            candidates.append(candidate)
            
            # Stop once we have enough candidates
            if len(candidates) >= top_k:
                break
        
        # Sort by combined score (descending)
        candidates.sort(key=lambda c: c.combined_score or 0, reverse=True)
        
        return candidates[:top_k]
    
    def _passes_filters(
        self,
        book: BookInDB,
        filters: UserPreferences
    ) -> bool:
        """
        Check if a book passes the user's preference filters.
        
        Args:
            book: Book to check
            filters: User preference filters
            
        Returns:
            True if book passes all filters
        """
        # Genre inclusion filter
        if filters.favorite_genres:
            # At least one genre should match
            if book.genre.lower() not in [g.lower() for g in filters.favorite_genres]:
                return False
        
        # Genre exclusion filter
        if filters.disliked_genres:
            if book.genre.lower() in [g.lower() for g in filters.disliked_genres]:
                return False
        
        # Rating filter
        if filters.min_rating is not None:
            if book.rating < filters.min_rating:
                return False
        
        return True
    
    def _calculate_metadata_score(self, book: BookInDB) -> float:
        """
        Calculate a normalized metadata score for a book.
        
        Combines rating and popularity into a single score.
        
        Args:
            book: Book to score
            
        Returns:
            Score between 0 and 1
        """
        # Normalize rating to 0-1 (assuming 0-5 scale)
        rating_score = book.rating / 5.0
        
        # Use popularity score if available, otherwise use rating as proxy
        popularity = book.popularity_score if book.popularity_score else rating_score
        
        # Blend: 60% rating, 40% popularity
        return (0.6 * rating_score) + (0.4 * popularity)


# Dependency injection function for FastAPI
def get_retrieval_service() -> RetrievalService:
    """
    Factory function for dependency injection.
    
    Using a function rather than a class instance allows for
    easier testing and configuration.
    """
    return RetrievalService()
