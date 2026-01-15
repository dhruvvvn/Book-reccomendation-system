"""
Utility Functions

General helper functions used across the application.
"""

import hashlib
from typing import Any, Dict, List, Optional
import re


def generate_book_id(title: str, author: str) -> str:
    """
    Generate a deterministic book ID from title and author.
    
    Args:
        title: Book title
        author: Author name
        
    Returns:
        A short hash-based ID
    """
    combined = f"{title.lower().strip()}:{author.lower().strip()}"
    return hashlib.sha256(combined.encode()).hexdigest()[:12]


def clean_description(text: str, max_length: int = 1000) -> str:
    """
    Clean and truncate book description.
    
    Removes extra whitespace and HTML tags.
    
    Args:
        text: Raw description text
        max_length: Maximum characters to keep
        
    Returns:
        Cleaned description
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    # Truncate if needed
    if len(text) > max_length:
        # Try to cut at sentence boundary
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        if last_period > max_length * 0.7:
            text = truncated[:last_period + 1]
        else:
            text = truncated.rsplit(' ', 1)[0] + '...'
    
    return text


def normalize_genre(genre: str) -> str:
    """
    Normalize genre names to standard categories.
    
    Args:
        genre: Raw genre string
        
    Returns:
        Normalized genre
    """
    genre = genre.lower().strip()
    
    # Genre mapping for common variations
    genre_map = {
        "sci-fi": "Science Fiction",
        "scifi": "Science Fiction", 
        "sf": "Science Fiction",
        "fantasy": "Fantasy",
        "romance": "Romance",
        "mystery": "Mystery",
        "thriller": "Thriller",
        "horror": "Horror",
        "non-fiction": "Non-Fiction",
        "nonfiction": "Non-Fiction",
        "biography": "Biography",
        "history": "History",
        "self-help": "Self-Help",
        "selfhelp": "Self-Help",
    }
    
    return genre_map.get(genre, genre.title())


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def safe_dict_get(d: Dict[str, Any], *keys, default: Any = None) -> Any:
    """
    Safely get nested dictionary values.
    
    Args:
        d: Dictionary to traverse
        *keys: Keys to follow
        default: Default value if key not found
        
    Returns:
        Value at nested key or default
    """
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key, default)
        else:
            return default
    return d
