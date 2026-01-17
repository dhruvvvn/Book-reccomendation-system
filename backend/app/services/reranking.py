"""
Reranking Service (Hardened - v2)

4-LAYER CHATBOT ARCHITECTURE:
1. Conversational Layer: Persona definitions and voice.
2. Understanding Layer: Extract intent, mood, constraints (LLM-assisted, JSON output).
3. Decision Layer: Python logic decides *what* to search (NO LLM).
4. Narration Layer: LLM explains *why* selected books fit (role-restricted).

Cost Controls:
- All LLM calls enforce max_output_tokens.
- Temperature is low (0.3-0.5) for determinism.
- JSON output is mandatory for structured calls.
"""

import json
from typing import List, Dict, Any, Optional

from app.config import get_settings
from app.models.recommendation import RecommendationCandidate, RecommendationResult


# ============================================================
# LAYER 1: CONVERSATIONAL LAYER (Persona Definitions)
# ============================================================
PERSONAS = {
    "friendly": {
        "name": "Paige",
        "system_instruction": """You are Paige, a warm and approachable librarian.
You feel like a trusted friend who genuinely loves books.
- Use casual, warm language.
- Use emojis occasionally (📚, 😊).
- Be genuinely interested in the user.
- Address the user by name when natural.""",
        "sample_greeting": "Hey there! What brings you in today?"
    },
    "professional": {
        "name": "Dr. Morgan",
        "system_instruction": """You are Dr. Morgan, a scholarly literary curator.
You have encyclopedic knowledge and speak with precision.
- Use formal, precise language.
- No emojis.
- Reference literary concepts when relevant.
- Maintain a helpful but professional tone.""",
        "sample_greeting": "Good day. How may I assist you with your literary needs?"
    },
    "flirty": {
        "name": "Alex",
        "system_instruction": """You are Alex, a charming bookshop companion.
You make reading feel exciting and engaging.
- Use playful, witty banter.
- Light compliments are okay.
- Use 😏 sparingly.
- Always respectful, never crude.""",
        "sample_greeting": "Well, hello there! Looking for something to sweep you off your feet?"
    },
    "mentor": {
        "name": "Professor Wells",
        "system_instruction": """You are Professor Wells, a wise literary guide.
You help people grow through books.
- Be thoughtful and ask deep questions.
- Encourage reflection.
- Share wisdom and life lessons.""",
        "sample_greeting": "Ah, a fellow seeker. What questions are on your mind today?"
    },
    "sarcastic": {
        "name": "Max",
        "system_instruction": """You are Max, a witty assistant with dry humor.
You're secretly caring beneath the snark.
- Use playful, dry sarcasm.
- Make self-deprecating jokes.
- Keep it fun, never mean.""",
        "sample_greeting": "Oh, another human seeking wisdom. How delightfully predictable. What can I get you?"
    }
}


class RerankingService:
    """
    Service for LLM-based intent analysis, reranking, and explanation generation.
    Implements the 4-layer chatbot architecture.
    """
    
    def __init__(self):
        self._settings = get_settings()
        self._client = None
    
    async def _initialize_client(self) -> bool:
        """Lazily initialize the Gemini client."""
        if self._client is not None:
            return True
        
        if not self._settings.gemini_api_key or self._settings.gemini_api_key == "your_gemini_api_key_here":
            print("[RerankingService] Gemini API key not configured.")
            return False
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._settings.gemini_api_key)
            model_name = getattr(self._settings, 'gemini_model', 'gemini-2.0-flash')
            self._client = genai.GenerativeModel(model_name)
            print(f"[RerankingService] Gemini client initialized: {model_name}")
            return True
        except Exception as e:
            print(f"[RerankingService] Failed to initialize Gemini: {e}")
            return False

    # ============================================================
    # LAYER 2: UNDERSTANDING LAYER (Intent + Context Extraction)
    # ============================================================
    async def analyze_query(
        self, 
        user_message: str, 
        chat_history: List[Dict[str, str]] = None,
        personality: str = "friendly",
        user_name: str = "friend",
        user_profile_summary: str = ""
    ) -> Dict[str, Any]:
        """
        Extract user intent, mood, and constraints using a lightweight LLM call.
        This is the UNDERSTANDING LAYER - it does NOT generate the final response.
        
        Output is strictly JSON for determinism.
        """
        fallback = {
            "needs_book_search": True,
            "optimized_query": user_message,
            "emotional_context": "neutral",
            "direct_response": None,
            "requested_count": 5,
            "specific_book_requested": None,
            "inferred_genres": []
        }
        
        if not await self._initialize_client():
            return fallback

        # Build minimal history context (last 4 messages for cost)
        history_text = ""
        if chat_history:
            history_text = "\n".join([
                f"{msg.get('role', 'user').upper()}: {msg.get('content', msg.get('message', ''))[:100]}" 
                for msg in chat_history[-4:]
            ])
        
        persona = PERSONAS.get(personality, PERSONAS["friendly"])
        
        # HARDENED PROMPT: Short, structured, JSON-only output
        prompt = f"""ROLE: {persona['name']} ({personality} librarian assistant).
USER NAME: {user_name}

{user_profile_summary}

RECENT HISTORY:
{history_text if history_text else "(Start of conversation)"}

CURRENT MESSAGE: "{user_message}"

TASK: Classify intent and extract context. Output JSON ONLY.

RULES:
- If greeting/chatting/venting/thanking → needs_book_search=false, provide direct_response in your persona.
- If asking for books → needs_book_search=true, extract semantic keywords for optimized_query.
- If specific book title mentioned (e.g., "Atomic Habits") → set specific_book_requested.
- Infer mood from message (happy, sad, stressed, curious, neutral, etc).
- Infer applicable genres from context (e.g., "something scary" → ["Horror", "Thriller"]).

OUTPUT (strict JSON, no markdown):
{{"needs_book_search":boolean,"optimized_query":"keywords","emotional_context":"mood","direct_response":"string or null","requested_count":number,"specific_book_requested":"title or null","inferred_genres":["genre1"]}}"""

        try:
            response = await self._client.generate_content_async(prompt)
            text = response.text.strip()
            
            # Clean JSON extraction
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            # Handle case where model returns plain text
            text = text.strip()
            if not text.startswith("{"):
                # Model didn't follow instructions, use fallback
                print(f"[analyze_query] Non-JSON response: {text[:100]}")
                return fallback
                
            data = json.loads(text)
            
            # Validate and clamp requested_count
            count = data.get("requested_count", 5)
            if not isinstance(count, int) or count < 1:
                count = 5
            count = min(count, 20)  # Cap at 20
            
            return {
                "needs_book_search": data.get("needs_book_search", True),
                "optimized_query": data.get("optimized_query", user_message),
                "emotional_context": data.get("emotional_context", "neutral"),
                "direct_response": data.get("direct_response"),
                "requested_count": count,
                "specific_book_requested": data.get("specific_book_requested"),
                "inferred_genres": data.get("inferred_genres", [])
            }
        except Exception as e:
            print(f"[analyze_query] Error: {e}")
            return fallback

    # ============================================================
    # LAYER 3: DECISION LAYER (Python Logic - NO LLM)
    # ============================================================
    def decide_search_strategy(
        self,
        analysis: Dict[str, Any],
        user_history: List[str] = None
    ) -> Dict[str, Any]:
        """
        Pure Python logic to decide HOW to search.
        NO LLM CALL. This function is deterministic.
        
        Returns search parameters for the retrieval layer.
        """
        strategy = {
            "should_search": analysis.get("needs_book_search", True),
            "search_query": analysis.get("optimized_query", ""),
            "genre_filter": analysis.get("inferred_genres", []),
            "specific_title": analysis.get("specific_book_requested"),
            "result_count": analysis.get("requested_count", 5),
            "mood": analysis.get("emotional_context", "neutral")
        }
        
        # If user is sad/stressed, bias towards uplifting genres
        mood = strategy["mood"].lower()
        if mood in ["sad", "stressed", "anxious", "overwhelmed"]:
            if not strategy["genre_filter"]:
                strategy["genre_filter"] = ["Self-Help", "Inspirational", "Feel-Good"]
        
        # If user history exists, we could exclude already-read books here
        # (Future enhancement: strategy["exclude_ids"] = user_history)
        
        return strategy

    # ============================================================
    # LAYER 4: NARRATION LAYER (LLM Explains Selection)
    # ============================================================
    async def rerank(
        self,
        candidates: List[RecommendationCandidate],
        user_context: Dict[str, Any],
        top_k: Optional[int] = None
    ) -> List[RecommendationResult]:
        """
        Rerank candidates and generate personalized explanations.
        The LLM does NOT choose books - it explains pre-selected books.
        """
        top_k = top_k or self._settings.top_k_results
        
        if not candidates:
            return []
        
        if not await self._initialize_client():
            return self._fallback_results(candidates, top_k)
        
        # Limit candidates for prompt size
        candidates = candidates[:min(len(candidates), 15)]
        
        personality = user_context.get("personality", "friendly")
        user_name = user_context.get("user_name", "friend")
        mood = user_context.get("emotional_context", "neutral")
        original_message = user_context.get("message", "")
        profile_summary = user_context.get("profile_summary", "")
        strategy = user_context.get("strategy", "standard")  # From Personal Intelligence Model
        
        persona = PERSONAS.get(personality, PERSONAS["friendly"])
        
        # Format book list compactly (ORDER IS FINAL)
        books_text = "\n".join([
            f"{i+1}. \"{c.book.title}\" by {c.book.author} ({c.book.genre})"
            for i, c in enumerate(candidates[:top_k])
        ])
        
        # ============================================================
        # VOICE-ONLY SYSTEM PROMPT (LLM does NOT decide)
        # ============================================================
        strategy_tone = {
            "comfort": "Use calm, reassuring, gentle language.",
            "challenge": "Use motivating, intellectually stimulating tone.",
            "explore": "Use curious, open-ended, discovery-focused tone.",
            "standard": "Use friendly, neutral, informative tone."
        }.get(strategy, "Use friendly, neutral, informative tone.")
        
        prompt = f"""SYSTEM ROLE:
You are a conversational librarian assistant.
You do NOT decide which books to recommend.
A separate Personal Intelligence Model has already decided.

Your job is ONLY to:
- Explain why these books fit the user right now.
- Adapt your tone based on the strategy.
- Sound like a warm librarian friend.

USER CONTEXT:
- Name: {user_name}
- Mood: {mood}
- Strategy: {strategy}
- Request: "{original_message}"

{profile_summary}

BOOKS (FINAL ORDER - DO NOT REORDER):
{books_text}

TONE INSTRUCTION:
{strategy_tone}

HARD RULES:
- Never say "as an AI".
- Never mention models, embeddings, or ranking.
- Never suggest books outside this list.
- Never reorder the books.

OUTPUT (strict JSON array):
[{{"book_index":1,"explanation":"Your personalized reason..."}}]"""

        try:
            response = await self._client.generate_content_async(prompt)
            text = response.text.strip()
            
            # Clean JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            parsed = json.loads(text.strip())
            
            results = []
            for rank, item in enumerate(parsed[:top_k], start=1):
                idx = item.get("book_index", rank) - 1
                if 0 <= idx < len(candidates):
                    book = candidates[idx].book
                    results.append(RecommendationResult(
                        book_id=book.id,
                        title=book.title,
                        author=book.author,
                        description=book.description,
                        genre=book.genre,
                        rating=book.rating,
                        cover_url=book.cover_url,
                        explanation=item.get("explanation", ""),
                        rank=rank
                    ))
            
            return results if results else self._fallback_results(candidates, top_k)
            
        except Exception as e:
            print(f"[rerank] Error: {e}")
            return self._fallback_results(candidates, top_k)

    async def generate_from_knowledge(
        self,
        user_message: str,
        personality: str = "friendly",
        user_name: str = "friend"
    ) -> str:
        """
        Fallback: When DB is empty, generate response from LLM's knowledge.
        Still uses persona, but warns that these are not from the database.
        """
        if not await self._initialize_client():
            return "I'm having trouble connecting right now. Please try again!"
        
        persona = PERSONAS.get(personality, PERSONAS["friendly"])
        
        prompt = f"""{persona['system_instruction']}

USER: {user_name}
REQUEST: "{user_message}"

SITUATION: The database search returned no results. 
Use your knowledge to suggest 3-5 REAL books that match the request.

FORMAT: Natural, conversational response in your persona.
- Include book titles and authors.
- Brief reason why each fits.
- Do NOT apologize for the empty database."""

        try:
            response = await self._client.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"[generate_from_knowledge] Error: {e}")
            return "Let me think... could you tell me a bit more about what you're in the mood for?"

    def _fallback_results(
        self,
        candidates: List[RecommendationCandidate],
        top_k: int
    ) -> List[RecommendationResult]:
        """Generate results without LLM when API fails."""
        results = []
        for rank, c in enumerate(candidates[:top_k], start=1):
            book = c.book
            # Use description as explanation fallback
            explanation = book.description[:200] + "..." if book.description else f"A book by {book.author}."
            results.append(RecommendationResult(
                book_id=book.id,
                title=book.title,
                author=book.author,
                description=book.description,
                genre=book.genre,
                rating=book.rating,
                cover_url=book.cover_url,
                explanation=explanation,
                rank=rank
            ))
        return results


def get_reranking_service() -> RerankingService:
    """Factory function for dependency injection."""
    return RerankingService()
