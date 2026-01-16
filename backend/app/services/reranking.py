"""
Reranking Service

Uses Gemini Pro LLM to rerank candidate books and generate
personalized, empathetic explanations.

Architecture Decision:
This service ONLY receives pre-retrieved candidates - it does NOT
perform any retrieval. This maintains clean separation of concerns
and prevents LLM hallucination about books that don't exist.
"""

import json
from typing import List, Dict, Any, Optional

from app.config import get_settings
from app.models.recommendation import RecommendationCandidate, RecommendationResult


class RerankingService:
    """
    Service for LLM-based reranking and explanation generation.
    
    Uses Gemini Pro to:
    1. Consider user context and emotional state
    2. Rerank candidate books by relevance
    3. Generate personalized explanations
    """
    
    def __init__(self):
        self._settings = get_settings()
        self._client = None
    
    async def _initialize_client(self) -> bool:
        """
        Initialize the Gemini client lazily.
        
        Returns:
            True if client initialized successfully, False otherwise
        """
        if self._client is not None:
            return True
        
        if not self._settings.gemini_api_key or self._settings.gemini_api_key == "your_gemini_api_key_here":
            print("Gemini API key not configured. Using fallback explanations.")
            return False
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._settings.gemini_api_key)
            self._client = genai.GenerativeModel('gemini-1.5-flash')
            return True
        except Exception as e:
            print(f"Failed to initialize Gemini client: {e}")
            return False
    
    async def rerank(
        self,
        candidates: List[RecommendationCandidate],
        user_context: Dict[str, Any],
        top_k: Optional[int] = None
    ) -> List[RecommendationResult]:
        """
        Rerank candidates and generate explanations.
        
        Args:
            candidates: Pre-retrieved book candidates
            user_context: Dict containing message, preferences, emotional_context
            top_k: Number of final recommendations (default from settings)
            
        Returns:
            Ranked list of RecommendationResult with explanations
        """
        top_k = top_k or self._settings.top_k_results
        
        if not candidates:
            return []
        
        # Try to initialize the Gemini client
        client_ready = await self._initialize_client()
        
        # If client not available (no API key), use fallback directly
        if not client_ready or self._client is None:
            return self._fallback_results(candidates, top_k)
        
        # Build the prompt for Gemini
        prompt = self._build_prompt(candidates, user_context, top_k)
        
        try:
            # Call Gemini API
            response = await self._client.generate_content_async(prompt)
            
            # Parse structured response
            results = self._parse_response(response.text, candidates, top_k)
            
            return results
            
        except Exception as e:
            # Fallback: Return top candidates without LLM explanations
            print(f"LLM reranking failed: {e}")
            return self._fallback_results(candidates, top_k)
    
    def _build_prompt(
        self,
        candidates: List[RecommendationCandidate],
        user_context: Dict[str, Any],
        top_k: int
    ) -> str:
        """
        Build the prompt for the LLM.
        
        The prompt instructs the LLM to:
        1. Consider the user's emotional state
        2. Rank books by relevance to their context
        3. Generate empathetic explanations
        """
        # Format book candidates for the prompt
        books_text = "\n".join([
            f"{i+1}. **{c.book.title}** by {c.book.author}\n"
            f"   Genre: {c.book.genre} | Rating: {c.book.rating}/5\n"
            f"   Description: {c.book.description[:300]}..."
            for i, c in enumerate(candidates[:20])  # Limit to 20 for context window
        ])
        
        user_message = user_context.get("message", "")
        emotional_context = user_context.get("emotional_context", "")
        
        prompt = f"""You are a compassionate book recommendation assistant. Your task is to select the {top_k} best books for this user and write deeply personalized explanations.

## User's Message
{user_message}

## User's Emotional Context
{emotional_context if emotional_context else "Not specified"}

## Candidate Books
{books_text}

## Instructions
1. Consider the user's emotional state and life context
2. Select the {top_k} most relevant books from the candidates
3. For each book, write a warm, empathetic explanation (2-3 sentences) of why it's perfect for them
4. Do NOT recommend books not in the candidate list

## Response Format (JSON)
Return a JSON array with exactly {top_k} objects:
```json
[
  {{
    "book_index": 1,
    "explanation": "Given that you're feeling...",
    "relevance_reasons": ["reason1", "reason2"],
    "confidence": 0.95
  }}
]
```

Only return the JSON array, no other text."""

        return prompt
    
    def _parse_response(
        self,
        response_text: str,
        candidates: List[RecommendationCandidate],
        top_k: int
    ) -> List[RecommendationResult]:
        """
        Parse the LLM response into RecommendationResult objects.
        """
        results: List[RecommendationResult] = []
        
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_text = response_text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0]
            
            parsed = json.loads(json_text.strip())
            
            for rank, item in enumerate(parsed[:top_k], start=1):
                book_idx = item.get("book_index", rank) - 1
                
                if 0 <= book_idx < len(candidates):
                    book = candidates[book_idx].book
                    
                    result = RecommendationResult(
                        book_id=book.id,
                        title=book.title,
                        author=book.author,
                        description=book.description,
                        genre=book.genre,
                        rating=book.rating,
                        cover_url=book.cover_url,
                        explanation=item.get("explanation", ""),
                        relevance_reasons=item.get("relevance_reasons"),
                        rank=rank,
                        confidence_score=item.get("confidence")
                    )
                    results.append(result)
                    
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Failed to parse LLM response: {e}")
            return self._fallback_results(candidates, top_k)
        
        return results
    
    def _fallback_results(
        self,
        candidates: List[RecommendationCandidate],
        top_k: int
    ) -> List[RecommendationResult]:
        """
        Generate fallback results without LLM explanations.
        
        Used when LLM call fails or response parsing fails.
        """
        results: List[RecommendationResult] = []
        
        for rank, candidate in enumerate(candidates[:top_k], start=1):
            book = candidate.book
            
            # Generate a meaningful explanation based on available data
            # Avoid showing "unknown" or "0.0/5" which looks broken
            if book.description and len(book.description) > 20:
                # Use description as the explanation
                desc_preview = book.description[:200] + "..." if len(book.description) > 200 else book.description
                explanation = desc_preview
            else:
                # Minimal fallback
                explanation = f"A book by {book.author} that matches your search."
            
            result = RecommendationResult(
                book_id=book.id,
                title=book.title,
                author=book.author,
                description=book.description,
                genre=book.genre,
                rating=book.rating,
                cover_url=book.cover_url,
                explanation=explanation,
                rank=rank
            )
            results.append(result)
        
        return results


def get_reranking_service() -> RerankingService:
    """Factory function for dependency injection."""
    return RerankingService()
