"""
Embedding Service

Handles text embedding generation using sentence-transformers.
Uses a singleton pattern to avoid reloading the model on every request.

Architecture Decision:
- Lazy loading: Model loads on first use, not at import time
- Thread-safe: Uses asyncio for CPU-bound operations
- Batching: Supports batch embedding for efficiency
"""

import asyncio
from functools import lru_cache
from typing import List, Optional
import numpy as np

from app.config import get_settings


class EmbeddingService:
    """
    Service for generating text embeddings using sentence-transformers.
    
    The model is loaded lazily on first use to avoid slow startup
    when the embedding service isn't immediately needed.
    """
    
    def __init__(self):
        self._model = None
        self._settings = get_settings()
        self._lock = asyncio.Lock()
    
    async def _load_model(self) -> None:
        """
        Load the sentence-transformer model.
        
        Uses a lock to prevent multiple concurrent loads.
        Called automatically on first embedding request.
        """
        if self._model is not None:
            return
        
        async with self._lock:
            # Double-check after acquiring lock
            if self._model is not None:
                return
            
            # Import here to avoid loading torch at module import time
            from sentence_transformers import SentenceTransformer
            
            print(f"Loading embedding model: {self._settings.embedding_model}")
            
            # Run model loading in thread pool (CPU-bound)
            loop = asyncio.get_event_loop()
            self._model = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer(self._settings.embedding_model)
            )
            
            print("Embedding model loaded successfully")
    
    async def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Numpy array of shape (embedding_dimension,)
        """
        await self._load_model()
        
        # Run encoding in thread pool (CPU-bound)
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: self._model.encode(text, convert_to_numpy=True)
        )
        
        return embedding
    
    async def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts (batch processing).
        
        More efficient than calling embed_text multiple times
        as the model can batch process.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Numpy array of shape (len(texts), embedding_dimension)
        """
        await self._load_model()
        
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self._model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=len(texts) > 100
            )
        )
        
        return embeddings
    
    @property
    def embedding_dimension(self) -> int:
        """Return the dimension of embeddings produced by the model."""
        return self._settings.embedding_dimension
    
    def is_loaded(self) -> bool:
        """Check if the model is currently loaded."""
        return self._model is not None


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """
    Get cached embedding service instance.
    
    Note: In the actual application, the service is stored in app.state
    for proper lifecycle management. This function is for standalone use.
    """
    return EmbeddingService()
