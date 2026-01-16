"""
Data Ingestion Script

Loads book data from JSON, generates embeddings, and stores them
in the FAISS vector store.

Usage:
    python -m scripts.ingest_data --input data/books_sample.json

This script is designed to be run once to populate the initial index,
or incrementally to add new books.
"""

import argparse
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.models.book import BookInDB
from app.services.embedding import EmbeddingService
from app.db.vector_store import VectorStore
from app.utils.helpers import generate_book_id, clean_description, normalize_genre


async def load_books_from_json(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load book data from a JSON file.
    
    Expected JSON format:
    [
        {
            "title": "Book Title",
            "author": "Author Name",
            "description": "Book description...",
            "genre": "Fiction",
            "rating": 4.5
        },
        ...
    ]
    """
    print(f"Loading books from {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        books = json.load(f)
    
    print(f"Loaded {len(books)} books")
    return books


def prepare_book_data(raw_books: List[Dict[str, Any]]) -> List[BookInDB]:
    """
    Convert raw JSON data to BookInDB objects.
    
    Performs cleaning and normalization:
    - Generates deterministic IDs
    - Cleans descriptions
    - Normalizes genres
    """
    books: List[BookInDB] = []
    
    for raw in raw_books:
        try:
            book = BookInDB(
                id=generate_book_id(raw["title"], raw["author"]),
                title=raw["title"].strip(),
                author=raw["author"].strip(),
                description=clean_description(raw.get("description", "")),
                genre=normalize_genre(raw.get("genre", "Unknown")),
                rating=float(raw.get("rating", 0)),
                cover_url=raw.get("cover_url"),
                popularity_score=raw.get("popularity_score")
            )
            books.append(book)
        except Exception as e:
            print(f"⚠️ Skipping invalid book: {raw.get('title', 'Unknown')} - {e}")
    
    return books


async def generate_embeddings(
    embedding_service: EmbeddingService,
    books: List[BookInDB],
    batch_size: int = 32
) -> Any:
    """
    Generate embeddings for all books.
    
    Uses batch processing for efficiency.
    Embeds the description field for semantic matching.
    """
    import numpy as np
    
    print(f"Generating embeddings for {len(books)} books...")
    
    # Prepare texts for embedding
    # Combine title + description for richer semantic representation
    texts = [
        f"{book.title} by {book.author}. {book.description}"
        for book in books
    ]
    
    # Process in batches
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"  Processing batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}")
        
        embeddings = await embedding_service.embed_texts(batch)
        all_embeddings.append(embeddings)
    
    # Stack all embeddings
    result = np.vstack(all_embeddings)
    
    print(f"Generated {len(result)} embeddings of dimension {result.shape[1]}")
    return result


async def main(input_file: str, force: bool = False):
    """
    Main ingestion pipeline.
    
    Args:
        input_file: Path to JSON file with book data
        force: If True, overwrite existing index
    """
    settings = get_settings()
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"❌ File not found: {input_path}")
        return
    
    # Check if index already exists
    index_path = Path(settings.faiss_index_path)
    books_path = index_path.with_suffix(".books.npy")

    if index_path.exists():
        if force:
            print(f"Force flag set. Removing existing index at {index_path}")
            try:
                if index_path.exists():
                    index_path.unlink()
                if books_path.exists():
                    books_path.unlink()
                print("Existing index files removed.")
            except Exception as e:
                print(f"Error removing index files: {e}")
                return
        else:
            print(f"Index already exists at {index_path}")
            print("   Use --force to overwrite")
            return
    
    # Initialize services
    print("\nInitializing services...")
    embedding_service = EmbeddingService()
    vector_store = VectorStore()
    await vector_store.initialize()
    
    # Load and prepare data
    raw_books = await load_books_from_json(input_path)
    books = prepare_book_data(raw_books)
    
    if not books:
        print("No valid books to process")
        return
    
    # Generate embeddings
    embeddings = await generate_embeddings(embedding_service, books)
    
    # Add to vector store
    print(f"\nAdding {len(books)} books to vector store...")
    ids = await vector_store.add(embeddings, books)
    print(f"Added books with IDs: {ids[0]} to {ids[-1]}")
    
    # Persist to disk
    await vector_store.persist()
    
    print(f"\nIngestion complete!")
    print(f"   Total books: {vector_store.size}")
    print(f"   Index path: {settings.faiss_index_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest book data into vector store")
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="data/books_sample.json",
        help="Path to input JSON file"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force overwrite existing index"
    )
    
    args = parser.parse_args()
    asyncio.run(main(args.input, args.force))
