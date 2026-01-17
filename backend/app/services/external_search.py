"""
External Book Search Service (Hardened - v2)

WATERFALL PATTERN:
1. Google Books API (Free, Accurate) - PRIMARY
2. Open Library API (Free, Backup) - SECONDARY  
3. LLM Generation (Costly, Last Resort) - FALLBACK

All JIT books are immediately persisted to SQLite.
"""

import json
import uuid
import aiohttp
from typing import Optional, List, Dict, Any

from app.config import get_settings
from app.models.book import BookInDB


class ExternalBookSearch:
    """
    JIT Book Discovery Service.
    
    Searches external sources when local DB fails.
    Follows strict cost hierarchy: API -> API -> LLM.
    """
    
    def __init__(self):
        self._settings = get_settings()
        self._client = None
    
    async def _initialize_gemini(self) -> bool:
        """Initialize Gemini client lazily."""
        if self._client is not None:
            return True
        
        if not self._settings.gemini_api_key or self._settings.gemini_api_key == "your_gemini_api_key_here":
            print("[ExternalSearch] Gemini API key not configured.")
            return False
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._settings.gemini_api_key)
            model_name = getattr(self._settings, 'gemini_model', 'gemini-flash-latest')
            self._client = genai.GenerativeModel(model_name)
            return True
        except Exception as e:
            print(f"[ExternalSearch] Gemini init failed: {e}")
            return False
    
    async def search(
        self, 
        query: str, 
        max_results: int = 3
    ) -> List[BookInDB]:
        """
        Search for books using the WATERFALL pattern:
        1. Google Books API (free)
        2. Open Library API (free)
        3. LLM fallback (costly)
        """
        print(f"[ExternalSearch] Query: '{query}'")
        
        # STEP 1: Google Books API (PRIMARY)
        books = await self._search_google_books(query, max_results)
        if books:
            print(f"[ExternalSearch] Google Books found {len(books)} results")
            return books
        
        # STEP 2: Open Library API (SECONDARY)
        books = await self._search_open_library(query, max_results)
        if books:
            print(f"[ExternalSearch] Open Library found {len(books)} results")
            return books
        
        # STEP 3: LLM Fallback (LAST RESORT)
        print("[ExternalSearch] APIs failed. Using LLM fallback...")
        return await self._search_via_llm(query, max_results)
    
    async def _search_google_books(self, query: str, max_results: int) -> List[BookInDB]:
        """Search Google Books API (no API key required for basic queries)."""
        try:
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.googleapis.com/books/v1/volumes?q={encoded_query}&maxResults={max_results}&printType=books"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    items = data.get("items", [])
                    
                    books = []
                    for item in items[:max_results]:
                        vol = item.get("volumeInfo", {})
                        
                        # Extract data with safe defaults
                        title = vol.get("title", "Unknown Title")
                        authors = vol.get("authors", ["Unknown Author"])
                        author = ", ".join(authors) if authors else "Unknown Author"
                        description = vol.get("description", "")[:500]
                        categories = vol.get("categories", ["General"])
                        genre = categories[0] if categories else "General"
                        rating = vol.get("averageRating", 4.0)
                        published = vol.get("publishedDate", "")[:4]
                        
                        # Cover URL
                        images = vol.get("imageLinks", {})
                        cover_url = images.get("thumbnail") or images.get("smallThumbnail")
                        
                        # Generate stable ID
                        book_id = f"gb_{uuid.uuid4().hex[:12]}"
                        
                        try:
                            year = int(published) if published.isdigit() else None
                        except:
                            year = None
                        
                        book = BookInDB(
                            id=book_id,
                            title=title,
                            author=author,
                            description=description,
                            genre=genre,
                            rating=min(5.0, max(0.0, float(rating))),
                            cover_url=cover_url,
                            year_published=year,
                            is_dynamic=True
                        )
                        books.append(book)
                    
                    return books
                    
        except Exception as e:
            print(f"[ExternalSearch] Google Books error: {e}")
            return []
    
    async def _search_open_library(self, query: str, max_results: int) -> List[BookInDB]:
        """Search Open Library API as backup."""
        try:
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            url = f"https://openlibrary.org/search.json?q={encoded_query}&limit={max_results}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    docs = data.get("docs", [])
                    
                    books = []
                    for doc in docs[:max_results]:
                        title = doc.get("title", "Unknown Title")
                        authors = doc.get("author_name", ["Unknown Author"])
                        author = ", ".join(authors[:2]) if authors else "Unknown Author"
                        subjects = doc.get("subject", ["General"])
                        genre = subjects[0][:50] if subjects else "General"
                        year = doc.get("first_publish_year")
                        
                        # Description from first sentence if available
                        description = doc.get("first_sentence", [""])[0] if doc.get("first_sentence") else ""
                        
                        # Cover
                        cover_id = doc.get("cover_i")
                        cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None
                        
                        book_id = f"ol_{uuid.uuid4().hex[:12]}"
                        
                        book = BookInDB(
                            id=book_id,
                            title=title,
                            author=author,
                            description=description[:500] if description else f"A book by {author}.",
                            genre=genre,
                            rating=4.0,  # Open Library doesn't have ratings
                            cover_url=cover_url,
                            year_published=year,
                            is_dynamic=True
                        )
                        books.append(book)
                    
                    return books
                    
        except Exception as e:
            print(f"[ExternalSearch] Open Library error: {e}")
            return []
    
    async def _search_via_llm(self, query: str, max_results: int) -> List[BookInDB]:
        """LLM fallback - only when APIs fail. Marked as AI-generated."""
        if not await self._initialize_gemini():
            return []
        
        # HARDENED PROMPT: Short, structured, JSON-only
        prompt = f"""TASK: Find {max_results} REAL books matching: "{query}"

OUTPUT (strict JSON array, no markdown):
[{{"title":"","author":"","description":"2 sentences max","genre":"","year":0,"rating":4.0}}]

RULES:
- Only real, published books
- No hallucinated awards or sales
- Neutral descriptions"""

        try:
            response = await self._client.generate_content_async(prompt)
            text = response.text.strip()
            
            # Clean JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            parsed = json.loads(text.strip())
            
            books = []
            for item in parsed[:max_results]:
                book_id = f"ai_{uuid.uuid4().hex[:12]}"
                
                # Try to get cover from Open Library
                cover_url = await self._get_cover_url(item.get("title"), item.get("author"))
                
                book = BookInDB(
                    id=book_id,
                    title=item.get("title", "Unknown"),
                    author=item.get("author", "Unknown"),
                    description=item.get("description", "")[:500] + " (Source: AI Generated)",
                    genre=item.get("genre", "General"),
                    rating=min(5.0, max(0.0, float(item.get("rating", 4.0)))),
                    cover_url=cover_url,
                    year_published=item.get("year"),
                    is_dynamic=True
                )
                books.append(book)
                print(f"[ExternalSearch] LLM found: '{book.title}' by {book.author}")
            
            return books
            
        except Exception as e:
            print(f"[ExternalSearch] LLM search error: {e}")
            return []
    
    async def _get_cover_url(self, title: str, author: str) -> Optional[str]:
        """Try to find a cover image for LLM-generated books."""
        try:
            import urllib.parse
            query = urllib.parse.quote(f"{title} {author}")
            url = f"https://openlibrary.org/search.json?q={query}&limit=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        docs = data.get("docs", [])
                        if docs and docs[0].get("cover_i"):
                            return f"https://covers.openlibrary.org/b/id/{docs[0]['cover_i']}-L.jpg"
        except:
            pass
        return None


def get_external_search_service() -> ExternalBookSearch:
    """Factory function for dependency injection."""
    return ExternalBookSearch()
