"""
FAISS Vector Store

Manages the FAISS index for fast similarity search.
Provides async wrappers around the CPU-bound FAISS operations.

Architecture Decision:
- Using FAISS over pgvector for simpler setup and faster in-memory operations
- Index is persisted to disk on shutdown and loaded on startup
- Book metadata is stored alongside the index for quick lookup
"""

import asyncio
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

from app.config import get_settings
from app.models.book import BookInDB


class VectorStore:
    """
    FAISS-based vector store for book embeddings.
    
    Stores embeddings in a FAISS index for fast approximate
    nearest neighbor search. Maintains a separate mapping
    from index IDs to book data.
    """
    
    def __init__(self):
        self._settings = get_settings()
        self._index = None
        self._books: Dict[int, BookInDB] = {}  # index_id -> book
        self._next_id: int = 0
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """
        Initialize the vector store.
        
        Attempts to load an existing index from disk.
        Creates a new index if none exists.
        """
        import faiss
        
        index_path = Path(self._settings.faiss_index_path)
        books_path = index_path.with_suffix(".books.npy")
        
        if index_path.exists() and books_path.exists():
            # Load existing index
            print(f"Loading FAISS index from {index_path}")
            
            loop = asyncio.get_event_loop()
            self._index = await loop.run_in_executor(
                None,
                lambda: faiss.read_index(str(index_path))
            )
            
            # Load book mapping
            books_data = np.load(str(books_path), allow_pickle=True).item()
            self._books = books_data.get("books", {})
            self._next_id = books_data.get("next_id", 0)
            
            print(f"Loaded {self._index.ntotal} vectors")
        else:
            # Create new index
            print("Creating new FAISS index")
            
            # Using IndexFlatIP for inner product (cosine similarity on normalized vectors)
            self._index = faiss.IndexFlatIP(self._settings.embedding_dimension)
            
            print("Empty FAISS index created")
    
    async def add(
        self,
        embeddings: np.ndarray,
        books: List[BookInDB]
    ) -> List[int]:
        """
        Add book embeddings to the index.
        
        Args:
            embeddings: Array of shape (n_books, embedding_dim)
            books: List of corresponding BookInDB objects
            
        Returns:
            List of assigned index IDs
        """
        async with self._lock:
            # Normalize embeddings for cosine similarity
            normalized = self._normalize(embeddings)
            
            # Assign IDs
            ids = list(range(self._next_id, self._next_id + len(books)))
            self._next_id += len(books)
            
            # Add to book mapping
            for idx, book in zip(ids, books):
                self._books[idx] = book
                book.embedding_id = idx
            
            # Add to FAISS index
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self._index.add(normalized.astype(np.float32))
            )
            
            return ids
    
    async def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for similar books.
        
        Args:
            query_embedding: Query vector of shape (embedding_dim,)
            top_k: Number of results to return
            
        Returns:
            List of dicts with 'book' and 'score' keys
        """
        if self._index is None or self._index.ntotal == 0:
            return []
        
        # Normalize query
        query = self._normalize(query_embedding.reshape(1, -1))
        
        # Search
        loop = asyncio.get_event_loop()
        scores, indices = await loop.run_in_executor(
            None,
            lambda: self._index.search(query.astype(np.float32), min(top_k, self._index.ntotal))
        )
        
        # Build results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            
            book = self._books.get(int(idx))
            if book:
                results.append({
                    "book": book,
                    "score": float(score)
                })
        
        return results
    
    async def persist(self) -> None:
        """
        Persist the index and book mapping to disk.
        """
        if self._index is None:
            return
        
        import faiss
        
        index_path = Path(self._settings.faiss_index_path)
        books_path = index_path.with_suffix(".books.npy")
        
        # Create directory if needed
        index_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Persisting FAISS index to {index_path}")
        
        # Save FAISS index
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: faiss.write_index(self._index, str(index_path))
        )
        
        # Save book mapping
        np.save(str(books_path), {
            "books": self._books,
            "next_id": self._next_id
        })
        
        print(f"Persisted {self._index.ntotal} vectors")
    
    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        """
        L2 normalize vectors for cosine similarity.
        
        FAISS IndexFlatIP computes inner product, which equals
        cosine similarity when vectors are L2 normalized.
        """
        norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
        return vectors / np.maximum(norms, 1e-8)
    
    @property
    def size(self) -> int:
        """Return the number of vectors in the index."""
        return self._index.ntotal if self._index else 0
    
    def is_initialized(self) -> bool:
        """Check if the index is initialized."""
        return self._index is not None
