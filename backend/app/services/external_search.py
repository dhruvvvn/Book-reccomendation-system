"""
External Book Search Service

When a book is not found in our local database, this service
uses Gemini to fetch book details from external knowledge and
returns structured data that can be added to our index.

This enables "infinite" knowledge - the system can recommend
ANY book, not just those in the original dataset.
"""

import json
import uuid
from typing import Optional, List, Dict, Any

from app.config import get_settings
from app.models.book import BookInDB


class ExternalBookSearch:
    """
    Service to search for books not in our database using Gemini.
    
    When the user asks for a specific book (like "Atomic Habits")
    that's not in our dataset, this service:
    1. Uses Gemini to get accurate book details
    2. Returns a structured BookInDB object
    3. Optionally provides a cover URL from Open Library
    """
    
    def __init__(self):
        self._settings = get_settings()
        self._client = None
    
    async def _initialize_client(self) -> bool:
        """Initialize the Gemini client lazily."""
        if self._client is not None:
            return True
        
        if not self._settings.gemini_api_key or self._settings.gemini_api_key == "your_gemini_api_key_here":
            print("ExternalBookSearch: Gemini API key not configured.")
            return False
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._settings.gemini_api_key)
            model_name = getattr(self._settings, 'gemini_model', 'gemini-2.0-flash')
            self._client = genai.GenerativeModel(model_name)
            return True
        except Exception as e:
            print(f"ExternalBookSearch: Failed to initialize Gemini: {e}")
            return False
    
    async def search(
        self, 
        query: str, 
        max_results: int = 3
    ) -> List[BookInDB]:
        """
        Search for books matching the query using Gemini's knowledge.
        
        Args:
            query: User's search query (e.g., "Atomic Habits by James Clear")
            max_results: Maximum number of books to return
            
        Returns:
            List of BookInDB objects with full metadata
        """
        print(f"DEBUG: ExternalBookSearch.search called for query: '{query}'")
        
        client_ready = await self._initialize_client()
        if not client_ready:
            print("DEBUG: ExternalBookSearch client failed to initialize")
            return []
        
        prompt = f"""You are a book database assistant. The user is looking for: "{query}"

Find {max_results} REAL books that best match this query. These must be actual published books.

For each book, provide accurate details in this exact JSON format:
```json
[
  {{
    "title": "Exact Book Title",
    "author": "Author Name",
    "description": "A compelling 2-3 sentence description of the book",
    "genre": "Primary genre (e.g., Self-Help, Fiction, Science Fiction, Romance, Biography)",
    "year_published": 2020,
    "rating": 4.5,
    "isbn": "ISBN-13 if known, otherwise null"
  }}
]
```

CRITICAL RULES:
- Only include books that ACTUALLY EXIST
- Be accurate with author names and publication years
- Rating should be a reasonable estimate (1.0 to 5.0)
- If the query mentions a specific book, prioritize finding exactly that book
- Return ONLY the JSON array, no other text
"""
        
        try:
            print("DEBUG: Sending request to Gemini...")
            response = await self._client.generate_content_async(prompt)
            text = response.text
            print(f"DEBUG: Gemini response received. Length: {len(text)}")
            print(f"DEBUG: Response preview: {text[:100]}...")
            
            # Extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            books_data = json.loads(text.strip())
            print(f"DEBUG: Parsed {len(books_data)} books from JSON")
            
            # Convert to BookInDB objects
            books = []
            for book_data in books_data[:max_results]:
                # Generate a unique ID for this dynamic book
                book_id = f"dyn_{uuid.uuid4().hex[:12]}"
                
                # Try to get cover from Open Library
                cover_url = await self._get_cover_url(
                    book_data.get("isbn"),
                    book_data.get("title"),
                    book_data.get("author")
                )
                
                book = BookInDB(
                    id=book_id,
                    title=book_data.get("title", "Unknown Title"),
                    author=book_data.get("author", "Unknown Author"),
                    description=book_data.get("description", ""),
                    genre=book_data.get("genre", "General"),
                    rating=min(5.0, max(0.0, float(book_data.get("rating", 4.0)))),
                    cover_url=cover_url,
                    year_published=book_data.get("year_published"),
                    is_dynamic=True  # Mark as dynamically added
                )
                books.append(book)
                print(f"ExternalBookSearch: Found '{book.title}' by {book.author}")
            
            return books
            
        except Exception as e:
            print(f"ExternalBookSearch: Failed to search: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _get_cover_url(
        self, 
        isbn: Optional[str], 
        title: str, 
        author: str
    ) -> Optional[str]:
        """
        Try to get a book cover from Open Library.
        
        Args:
            isbn: ISBN-13 if available
            title: Book title
            author: Author name
            
        Returns:
            Cover URL or None
        """
        import urllib.parse
        
        # Try ISBN first (most reliable)
        if isbn and isbn != "null":
            clean_isbn = isbn.replace("-", "").strip()
            if len(clean_isbn) in [10, 13]:
                return f"https://covers.openlibrary.org/b/isbn/{clean_isbn}-L.jpg"
        
        # Fallback: Search by title
        try:
            import aiohttp
            
            search_query = urllib.parse.quote(f"{title} {author}")
            search_url = f"https://openlibrary.org/search.json?q={search_query}&limit=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        docs = data.get("docs", [])
                        if docs and docs[0].get("cover_i"):
                            cover_id = docs[0]["cover_i"]
                            return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
        except Exception as e:
            print(f"ExternalBookSearch: Cover lookup failed: {e}")
        
        return None


def get_external_search_service() -> ExternalBookSearch:
    """Factory function for dependency injection."""
    return ExternalBookSearch()
