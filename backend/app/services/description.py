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
        """
        Generate description with strict cost control.
        ORDER: Google Books -> Gemini (LLM)
        """
        
        # 1. Google Books (Free, Accurate, Fast)
        google_result = await self._try_google_books(title, author)
        if google_result:
            return google_result
            
        # 2. Gemini Fallback (Costly, Last Resort)
        gemini_result = await self._try_gemini(title, author, genre)
        if gemini_result:
            return gemini_result
        
        # 3. Ultimate Fallback
        return "Description not available. (Source: System)"
    
    async def _try_gemini(self, title: str, author: str, genre: str) -> str:
        """Try generating description with Gemini. Returns formatted text."""
        if not await self._initialize_client():
            return None
        
        # Strict instruction for factual, dry summary
        prompt = f"""Task: Write a concise, factual summary for the book "{title}" by {author}.
Genre: {genre or 'General'}

Constraints:
- Max 3 sentences.
- Neutral tone.
- NO marketing language ("must-read", "thrilling").
- Start directly with the summary.
"""

        try:
            response = await asyncio.wait_for(
                self._client.generate_content_async(prompt),
                timeout=self._timeout_seconds
            )
            text = response.text.strip()
            # Mark it so we know it came from AI
            return f"{text} (Source: AI Generated)"
        except asyncio.TimeoutError:
            print(f"[DescriptionService] Gemini timeout for '{title}'")
            return None
        except Exception as e:
            print(f"[DescriptionService] Gemini error: {e}")
            return None
    
    async def _try_google_books(self, title: str, author: str) -> str:
        """
        Primary Source: Fetch description from Google Books API.
        Strategy:
        1. Strict search (intitle + inauthor)
        2. Loose search (q = title + author)
        3. Snippet fallback if description missing
        """
        import aiohttp
        import urllib.parse
        
        async def fetch(query_params):
            url = f"https://www.googleapis.com/books/v1/volumes?{query_params}&maxResults=1&printType=books"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                        if response.status == 200:
                            return await response.json()
            except Exception:
                pass
            return None

        # Attempt 1: Strict Search
        q_strict = f"intitle:{title}"
        if author and author != "Unknown":
            q_strict += f"+inauthor:{author}"
        
        data = await fetch(f"q={urllib.parse.quote(q_strict)}")
        
        # Attempt 2: Loose Search (if strict failed)
        if not data or "items" not in data:
            q_loose = f"{title} {author}"
            data = await fetch(f"q={urllib.parse.quote(q_loose)}")
            
        if data and "items" in data and len(data["items"]) > 0:
            vol = data["items"][0].get("volumeInfo", {})
            search_info = data["items"][0].get("searchInfo", {})
            
            # Priority 1: Full Description
            description = vol.get("description", "")
            
            # Priority 2: Text Snippet
            if not description:
                description = search_info.get("textSnippet", "")
            
            # Clean up HTML tags
            if description:
                import re
                clean_desc = re.sub('<[^<]+?>', '', description)
                
                # Truncate if unreasonably long
                if len(clean_desc) > 800:
                    clean_desc = clean_desc[:797] + "..."
                    
                return clean_desc
        
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
