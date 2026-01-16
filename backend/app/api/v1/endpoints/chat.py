"""
Chat Endpoint

Main conversational interface for book recommendations.
Now with PERSISTENT MEMORY and PER-USER PERSONALITY.

Features:
- Remembers users across sessions (stored in database)
- Adapts personality based on user preference (flirty, professional, friendly, etc.)
- Full conversation history for context-aware responses
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from typing import List, Dict, Optional
import traceback
import uuid

from app.models.chat import ChatRequest, ChatResponse
from app.models.recommendation import RecommendationResult
from app.services.retrieval import RetrievalService, get_retrieval_service
from app.services.reranking import RerankingService, get_reranking_service
from app.db.database import get_database

router = APIRouter()

# Fallback in-memory sessions for anonymous users
_anonymous_sessions: Dict[str, List[Dict[str, str]]] = {}


# ============ PERSONALITY DEFINITIONS ============

PERSONALITY_STYLES = {
    "friendly": {
        "name": "Paige",
        "description": "A warm, approachable librarian who feels like a trusted friend",
        "traits": "Warm, genuine, uses casual language, shares personal favorites, uses emojis occasionally 📚",
        "greeting": "Hey there! Welcome to my little corner of the literary world. What brings you in today?",
        "example": "Oh, I totally get that feeling! When I'm stressed, I love curling up with something cozy."
    },
    "professional": {
        "name": "Dr. Morgan",
        "description": "A scholarly curator with encyclopedic knowledge",
        "traits": "Precise, knowledgeable, formal but not cold, uses literary references, no emojis",
        "greeting": "Good day. I am at your service for literary consultation. How may I assist you?",
        "example": "Based on your stated preferences, I would recommend considering works in the psychological thriller genre."
    },
    "flirty": {
        "name": "Alex",
        "description": "A charming, playful bookshop companion who makes reading feel exciting",
        "traits": "Playful, uses compliments, witty banter, teasing but respectful, uses 😏 sparingly",
        "greeting": "Well, hello there! *leans against the bookshelf* Looking for something to sweep you off your feet?",
        "example": "A reader with taste like yours? Oh, I like you already. Let me find something perfect for you..."
    },
    "mentor": {
        "name": "Professor Wells",
        "description": "A wise, guiding figure who helps you grow through books",
        "traits": "Thoughtful, asks deep questions, encourages reflection, shares life wisdom",
        "greeting": "Ah, a fellow seeker of knowledge. What questions are stirring in your mind today?",
        "example": "Sometimes the books we need aren't the ones we think we want. What's really weighing on your heart?"
    },
    "sarcastic": {
        "name": "Max",
        "description": "A witty, dry-humored assistant with playful teasing",
        "traits": "Dry humor, playful sarcasm, secretly caring, self-deprecating jokes",
        "greeting": "Oh, another human seeking the wisdom of books. How delightfully predictable. What can I get you?",
        "example": "Let me guess - you want something 'unique' that 'no one has read before'? *adjusts glasses* I'll see what I can do."
    }
}


def get_user_context(user_id: Optional[int]) -> Dict:
    """
    Load user profile, personality, and chat history from database.
    Returns context dict for personalized responses.
    """
    if not user_id:
        return {
            "is_anonymous": True,
            "personality": "friendly",
            "display_name": "friend",
            "chat_history": [],
            "insights": []
        }
    
    db = get_database()
    user = db.get_user(user_id)
    
    if not user:
        return {
            "is_anonymous": True,
            "personality": "friendly",
            "display_name": "friend",
            "chat_history": [],
            "insights": []
        }
    
    # Load persistent chat history
    chat_history = db.get_chat_history(user_id, limit=20)
    
    # Load user insights (things the AI has learned)
    insights = db.get_user_insights(user_id)
    
    return {
        "is_anonymous": False,
        "user_id": user_id,
        "personality": user.get("personality", "friendly"),
        "display_name": user.get("display_name", user.get("username", "friend")),
        "chat_history": chat_history,
        "insights": insights,
        "favorite_genres": user.get("favorite_genres", "[]")
    }


def save_to_history(user_id: Optional[int], session_id: str, role: str, content: str):
    """Save message to database (if logged in) or in-memory (if anonymous)."""
    if user_id:
        db = get_database()
        db.add_chat_message(user_id, role, content)
    else:
        # Anonymous fallback
        if session_id not in _anonymous_sessions:
            _anonymous_sessions[session_id] = []
        _anonymous_sessions[session_id].append({"role": role, "content": content})
        # Limit anonymous history
        if len(_anonymous_sessions[session_id]) > 20:
            _anonymous_sessions[session_id] = _anonymous_sessions[session_id][-20:]


@router.post("", response_model=ChatResponse)
async def get_recommendations(
    request: Request,
    chat_request: ChatRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    reranking_service: RerankingService = Depends(get_reranking_service)
) -> ChatResponse:
    """
    Process user message with PERSISTENT MEMORY and PERSONALITY.
    
    If user_id is provided:
    - Load their personality preference
    - Load their chat history from database
    - Save new messages to database
    
    If anonymous:
    - Use in-memory session storage
    - Default to "friendly" personality
    """
    try:
        # Get services from app state
        embedding_service = request.app.state.embedding_service
        vector_store = request.app.state.vector_store
        
        # Get user context (personality, history, insights)
        user_id = getattr(chat_request, 'user_id', None)
        session_id = getattr(chat_request, 'session_id', None) or str(uuid.uuid4())
        
        user_context = get_user_context(user_id)
        personality = user_context["personality"]
        display_name = user_context["display_name"]
        
        # Get chat history (from DB for logged-in, or anonymous session)
        if user_context["is_anonymous"]:
            if session_id not in _anonymous_sessions:
                _anonymous_sessions[session_id] = []
            chat_history = _anonymous_sessions[session_id]
        else:
            chat_history = user_context["chat_history"]
        
        # Save user message
        save_to_history(user_id, session_id, "user", chat_request.message)
        
        # Get personality style
        style = PERSONALITY_STYLES.get(personality, PERSONALITY_STYLES["friendly"])
        
        print(f"[User: {display_name}] Personality: {personality} | Message: '{chat_request.message}'")
        
        # Step 1: Analyze user intent with personality context
        analysis = await reranking_service.analyze_query(
            user_message=chat_request.message,
            chat_history=chat_history,
            personality=personality,
            user_name=display_name
        )
        
        needs_book_search = analysis.get("needs_book_search", True)
        optimized_query = analysis.get("optimized_query", chat_request.message)
        emotional_context = analysis.get("emotional_context", "neutral")
        direct_response = analysis.get("direct_response")
        requested_count = analysis.get("requested_count", 5)  # Default to 5
        
        print(f"  -> needs_book_search: {needs_book_search}")
        print(f"  -> emotional_context: '{emotional_context}'")
        print(f"  -> requested_count: {requested_count}")
        
        # Step 2: If just chatting, return direct response
        if not needs_book_search and direct_response:
            save_to_history(user_id, session_id, "assistant", direct_response)
            return ChatResponse(
                message=direct_response,
                recommendations=[],
                query_understood=True,
                session_id=session_id
            )
        
        # Step 3: Book search flow
        query_embedding = await embedding_service.embed_text(optimized_query)
        
        candidates = await retrieval_service.retrieve(
            query_embedding=query_embedding,
            vector_store=vector_store,
            filters=chat_request.preferences
        )
        
        recommendations: List[RecommendationResult] = await reranking_service.rerank(
            candidates=candidates,
            user_context={
                "message": chat_request.message,
                "preferences": chat_request.preferences,
                "emotional_context": emotional_context,
                "chat_history": chat_history[-4:],
                "personality": personality,
                "user_name": display_name
            },
            top_k=requested_count  # Use extracted count
        )
        
        # Deduplicate recommendations by book_id
        seen_ids = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec.book_id not in seen_ids:
                seen_ids.add(rec.book_id)
                unique_recommendations.append(rec)
        recommendations = unique_recommendations[:requested_count]
        
        # Generate personality-aware response
        if not recommendations:
            # DATABASE EMPTY: Use Gemini's own knowledge instead of saying "I found nothing"
            print("  -> No database results. Asking Gemini to recommend from its own knowledge...")
            gemini_response = await reranking_service.generate_from_knowledge(
                user_message=chat_request.message,
                personality=personality,
                user_name=display_name
            )
            save_to_history(user_id, session_id, "assistant", gemini_response)
            return ChatResponse(
                message=gemini_response,
                recommendations=[],
                query_understood=True,
                session_id=session_id
            )
        else:
            if personality == "professional":
                message = f"I have identified {len(recommendations)} titles that align with your criteria:"
            elif personality == "flirty":
                message = f"Oh, I found some gems for you! {len(recommendations)} books that I think you'll absolutely fall for:"
            elif personality == "sarcastic":
                message = f"Against all odds, I found {len(recommendations)} books you might actually enjoy:"
            elif personality == "mentor":
                message = f"I've selected {len(recommendations)} books that I believe will serve your journey:"
            else:
                message = f"I've picked out {len(recommendations)} books I think you'll love:"
        
        # Save assistant response
        save_to_history(user_id, session_id, "assistant", message)
        
        return ChatResponse(
            message=message,
            recommendations=recommendations,
            query_understood=True,
            session_id=session_id
        )
        
    except Exception as e:
        print(f"Error in get_recommendations: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


@router.post("/stream")
async def get_recommendations_stream(
    chat_request: ChatRequest
):
    """
    Streaming version of recommendations endpoint.
    
    TODO: Implement Server-Sent Events (SSE) for:
    - Progress updates during retrieval
    - Streaming LLM explanation generation
    """
    raise NotImplementedError("Streaming not yet implemented")
