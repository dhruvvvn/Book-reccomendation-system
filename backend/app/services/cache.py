"""
Cache Service

Provides in-memory caching for expensive operations:
- Query embeddings (repeated queries)
- Retrieval results (same query + filters)

Using cachetools for TTL-based expiration and size limits.
"""

from typing import Any, Optional, Callable, TypeVar
from functools import wraps
import hashlib
import json

from cachetools import TTLCache

from app.config import get_settings


T = TypeVar('T')


class CacheService:
    """
    In-memory cache service with TTL and size limits.
    
    Provides separate caches for different use cases:
    - embedding_cache: Query string -> embedding vector
    - retrieval_cache: (query_hash, filters_hash) -> candidates
    """
    
    def __init__(self):
        settings = get_settings()
        
        # Cache for query embeddings
        self._embedding_cache: TTLCache = TTLCache(
            maxsize=settings.cache_max_size,
            ttl=settings.cache_ttl_seconds
        )
        
        # Cache for retrieval results
        self._retrieval_cache: TTLCache = TTLCache(
            maxsize=settings.cache_max_size // 2,
            ttl=settings.cache_ttl_seconds
        )
        
        # Cache statistics
        self._stats = {
            "embedding_hits": 0,
            "embedding_misses": 0,
            "retrieval_hits": 0,
            "retrieval_misses": 0
        }
    
    def get_embedding(self, query: str) -> Optional[Any]:
        """
        Get cached embedding for a query.
        
        Args:
            query: The query string
            
        Returns:
            Cached embedding or None if not found
        """
        key = self._hash_string(query)
        result = self._embedding_cache.get(key)
        
        if result is not None:
            self._stats["embedding_hits"] += 1
        else:
            self._stats["embedding_misses"] += 1
        
        return result
    
    def set_embedding(self, query: str, embedding: Any) -> None:
        """
        Cache an embedding for a query.
        
        Args:
            query: The query string
            embedding: The embedding to cache
        """
        key = self._hash_string(query)
        self._embedding_cache[key] = embedding
    
    def get_retrieval(self, query: str, filters: Optional[dict]) -> Optional[Any]:
        """
        Get cached retrieval results.
        
        Args:
            query: The query string
            filters: Optional filter parameters
            
        Returns:
            Cached candidates or None if not found
        """
        key = self._get_retrieval_key(query, filters)
        result = self._retrieval_cache.get(key)
        
        if result is not None:
            self._stats["retrieval_hits"] += 1
        else:
            self._stats["retrieval_misses"] += 1
        
        return result
    
    def set_retrieval(
        self,
        query: str,
        filters: Optional[dict],
        candidates: Any
    ) -> None:
        """
        Cache retrieval results.
        
        Args:
            query: The query string
            filters: Optional filter parameters
            candidates: The candidates to cache
        """
        key = self._get_retrieval_key(query, filters)
        self._retrieval_cache[key] = candidates
    
    def _hash_string(self, s: str) -> str:
        """Create a hash key from a string."""
        return hashlib.md5(s.encode()).hexdigest()
    
    def _get_retrieval_key(self, query: str, filters: Optional[dict]) -> str:
        """Create a composite key from query and filters."""
        filters_str = json.dumps(filters, sort_keys=True) if filters else ""
        combined = f"{query}:{filters_str}"
        return self._hash_string(combined)
    
    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dict with hit/miss counts for each cache
        """
        return {
            **self._stats,
            "embedding_cache_size": len(self._embedding_cache),
            "retrieval_cache_size": len(self._retrieval_cache)
        }
    
    def clear(self) -> None:
        """Clear all caches."""
        self._embedding_cache.clear()
        self._retrieval_cache.clear()
        self._stats = {k: 0 for k in self._stats}


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get the singleton cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
