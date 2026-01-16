"""
JIT Description Service

Generates book descriptions on-demand using Gemini, with:
- 10-second timeout to prevent freezing
- Persistence to JSON for caching
- Graceful fallback on failure
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Dict
from functools import lru_cache

from app.config import get_settings


class DescriptionService:
    """
    Service for Just-In-Time description generation and persistence.
    
    Workflow:
    1. Check if book already has description in memory/JSON
    2. If not, generate using Gemini with 10s timeout
    3. Persist to JSON immediately after generation
    4. Return description (or fallback message)
    """
    
    # In-memory cache of generated descriptions (book_id -> description)
    _description_cache: Dict[str, str] = {}
    
    def __init__(self):
        self._settings = get_settings()
        self._client = None
        self._data_path = Path("data/books_kindle.json")
        self._descriptions_path = Path("data/descriptions_cache.json")
        self._timeout_seconds = 10
        
    async def _initialize_client(self) -> bool:
        """Lazily initialize Gemini client."""
        if self._client is not None:
            return True
        
        if not self._settings.gemini_api_key:
            return False
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._settings.gemini_api_key)
            model_name = getattr(self._settings, 'gemini_model', 'gemini-flash-latest')
            self._client = genai.GenerativeModel(model_name)
            return True
        except Exception as e:
            print(f"[DescriptionService] Failed to init Gemini: {e}")
            return False
    
    async def get_or_generate(
        self,
        book_id: str,
        title: str,
        author: str,
        genre: str = ""
    ) -> str:
        """
        Get existing description or generate a new one.
        
        Args:
            book_id: Unique book identifier
            title: Book title
            author: Author name
            genre: Optional genre for context
            
        Returns:
            Book description (or fallback message)
        """
        # 1. Check in-memory cache first
        if book_id in self._description_cache:
            return self._description_cache[book_id]
        
        # 2. Check persisted descriptions
        persisted = await self._load_persisted_description(book_id)
        if persisted:
            self._description_cache[book_id] = persisted
            return persisted
        
        # 3. Generate new description with timeout
        description = await self._generate_with_timeout(title, author, genre)
        
        # 4. Persist and cache
        if description and not description.startswith("Description"):
            self._description_cache[book_id] = description
            await self._persist_description(book_id, description)
        
        return description
    
    async def _generate_with_timeout(
        self,
        title: str,
        author: str,
        genre: str
    ) -> str:
        """Generate description with strict timeout. Falls back to Google Books."""
        
        # Try Gemini first
        gemini_result = await self._try_gemini(title, author, genre)
        if gemini_result and not gemini_result.startswith("Description"):
            return gemini_result
        
        # Fallback: Google Books API (no API key needed)
        google_result = await self._try_google_books(title, author)
        if google_result:
            return google_result
        
        return "Description not available."
    
    async def _try_gemini(self, title: str, author: str, genre: str) -> str:
        """Try generating description with Gemini."""
        if not await self._initialize_client():
            return None
        
        prompt = f"""Write a 2-3 sentence engaging summary of the book "{title}" by {author}.
Genre: {genre or 'General'}

Focus on what makes this book compelling and who would enjoy it.
Be factual - this is a real book. Keep it brief and enticing."""

        try:
            response = await asyncio.wait_for(
                self._client.generate_content_async(prompt),
                timeout=self._timeout_seconds
            )
            return response.text.strip()
        except asyncio.TimeoutError:
            print(f"[DescriptionService] Gemini timeout for '{title}'")
            return None
        except Exception as e:
            print(f"[DescriptionService] Gemini error: {e}")
            return None
    
    async def _try_google_books(self, title: str, author: str) -> str:
        """Fallback: Fetch description from Google Books API."""
        import aiohttp
        
        try:
            query = f"intitle:{title}+inauthor:{author}"
            url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "items" in data and len(data["items"]) > 0:
                            vol = data["items"][0].get("volumeInfo", {})
                            description = vol.get("description", "")
                            if description:
                                # Truncate if too long
                                if len(description) > 500:
                                    description = description[:497] + "..."
                                return description
        except Exception as e:
            print(f"[DescriptionService] Google Books error: {e}")
        
        return None
    
    async def _load_persisted_description(self, book_id: str) -> Optional[str]:
        """Load description from persisted JSON cache."""
        try:
            if self._descriptions_path.exists():
                with open(self._descriptions_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    return cache.get(book_id)
        except Exception:
            pass
        return None
    
    async def _persist_description(self, book_id: str, description: str):
        """Save description to persistent JSON cache."""
        try:
            cache = {}
            if self._descriptions_path.exists():
                with open(self._descriptions_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            
            cache[book_id] = description
            
            with open(self._descriptions_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[DescriptionService] Failed to persist description: {e}")


# Singleton instance
_description_service: Optional[DescriptionService] = None


def get_description_service() -> DescriptionService:
    """Factory function for dependency injection."""
    global _description_service
    if _description_service is None:
        _description_service = DescriptionService()
    return _description_service
