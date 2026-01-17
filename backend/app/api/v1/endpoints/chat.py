"""
Chat Endpoint (Hardened - v2)

4-LAYER ARCHITECTURE INTEGRATION:
1. Conversational Layer: Persona handling is centralized in reranking.py
2. Understanding Layer: analyze_query extracts intent.
3. Decision Layer: decide_search_strategy computes search params (Python, no LLM).
4. Narration Layer: rerank generates explanations.

This endpoint orchestrates the layers cleanly.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from typing import List, Dict, Optional
import traceback
import uuid

from app.models.chat import ChatRequest, ChatResponse
from app.models.recommendation import RecommendationResult, RecommendationCandidate
from app.models.book import BookInDB
from app.services.retrieval import RetrievalService, get_retrieval_service
from app.services.reranking import RerankingService, get_reranking_service, PERSONAS
from app.services.profile import UserProfileService
from app.services.personal_intelligence import get_personal_intelligence_service
from app.db.database import get_database

router = APIRouter()

# Fallback in-memory sessions for anonymous users
_anonymous_sessions: Dict[str, List[Dict[str, str]]] = {}


def get_user_context(user_id: Optional[int]) -> Dict:
    """Load user profile, personality, and chat history from database."""
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
    
    chat_history = db.get_chat_history(user_id, limit=20)
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
        if session_id not in _anonymous_sessions:
            _anonymous_sessions[session_id] = []
        _anonymous_sessions[session_id].append({"role": role, "content": content})
        if len(_anonymous_sessions[session_id]) > 20:
            _anonymous_sessions[session_id] = _anonymous_sessions[session_id][-20:]


def generate_persona_message(personality: str, book_count: int) -> str:
    """Generate a persona-appropriate intro message for recommendations."""
    persona = PERSONAS.get(personality, PERSONAS["friendly"])
    name = persona["name"]
    
    templates = {
        "friendly": f"I found {book_count} books I think you'll love! 📚",
        "professional": f"I have identified {book_count} titles that align with your criteria.",
        "flirty": f"Oh, I found some gems for you! {book_count} books I think you'll fall for 😏",
        "mentor": f"I've selected {book_count} books that I believe will serve your journey.",
        "sarcastic": f"Against all odds, I found {book_count} books you might actually enjoy."
    }
    return templates.get(personality, templates["friendly"])


@router.post("", response_model=ChatResponse)
async def get_recommendations(
    request: Request,
    chat_request: ChatRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    reranking_service: RerankingService = Depends(get_reranking_service)
) -> ChatResponse:
    """
    Main chat endpoint with 4-layer architecture.
    
    Flow:
    1. UNDERSTANDING: Analyze intent & extract context (LLM).
    2. DECISION: Decide search strategy (Python).
    3. RETRIEVAL: Vector search + SQL fallback.
    4. NARRATION: Generate personalized explanations (LLM).
    """
    try:
        embedding_service = request.app.state.embedding_service
        vector_store = request.app.state.vector_store
        
        user_id = getattr(chat_request, 'user_id', None)
        session_id = getattr(chat_request, 'session_id', None) or str(uuid.uuid4())
        
        user_context = get_user_context(user_id)
        personality = user_context["personality"]
        display_name = user_context["display_name"]
        
        if user_context["is_anonymous"]:
            if session_id not in _anonymous_sessions:
                _anonymous_sessions[session_id] = []
            chat_history = _anonymous_sessions[session_id]
        else:
            chat_history = user_context["chat_history"]
        
        save_to_history(user_id, session_id, "user", chat_request.message)
        
        # ============ GENERATE USER PROFILE SUMMARY ============
        db = get_database()
        profile_service = UserProfileService(db)
        profile_summary = profile_service.get_profile_summary(user_id) if user_id else ""
        
        print(f"[Chat] User: {display_name} | Persona: {personality} | Msg: '{chat_request.message[:50]}...'")
        
        # ============ LAYER 2: UNDERSTANDING ============
        analysis = await reranking_service.analyze_query(
            user_message=chat_request.message,
            chat_history=chat_history,
            personality=personality,
            user_name=display_name,
            user_profile_summary=profile_summary
        )
        
        needs_search = analysis.get("needs_book_search", True)
        direct_response = analysis.get("direct_response")
        
        print(f"  -> Intent: {'SEARCH' if needs_search else 'CHAT'} | Mood: {analysis.get('emotional_context')}")
        
        # If just chatting, return direct response (no DB hit)
        if not needs_search and direct_response:
            save_to_history(user_id, session_id, "assistant", direct_response)
            return ChatResponse(
                message=direct_response,
                recommendations=[],
                query_understood=True,
                session_id=session_id
            )
        
        # ============ LAYER 3: DECISION (Python, no LLM) ============
        search_strategy = reranking_service.decide_search_strategy(analysis)
        
        optimized_query = search_strategy["search_query"]
        requested_count = search_strategy["result_count"]
        specific_book = search_strategy["specific_title"]
        mood = analysis.get("emotional_context", "neutral")
        
        # ============ PERSONAL INTELLIGENCE: Strategy ============
        pi_service = get_personal_intelligence_service()
        strategy = pi_service.predict_strategy(mood)
        
        print(f"  -> Search: '{optimized_query}' | Count: {requested_count} | Strategy: {strategy}")
        
        # ============ LOG SEARCH QUERY FOR PERSONALIZATION ============
        if user_id:
            db.log_search_query(user_id, optimized_query)
        
        # ============ TITLE VERIFICATION GUARDRAIL ============
        # If user asks for specific book, try to find it locally. 
        # If missing, FALLBACK TO GOOGLE BOOKS (JIT) instead of vector search.
        
        candidates = []
        jit_book_found = False
        
        if specific_book:
            print(f"  -> User requested specific book: '{specific_book}'")
            # 1. Try fuzzy match in local Vector Store
            local_matches = [
                b for b in vector_store._books.values() 
                if specific_book.lower() in b.title.lower()
            ]
            
            if local_matches:
                print(f"  -> Found {len(local_matches)} local matches.")
                # Use local matches as candidates
                for match in local_matches[:3]:  # Top 3 local matches
                    candidates.append(RecommendationCandidate(
                        book=match,
                        similarity_score=2.0,
                        metadata_score=1.0,
                        combined_score=2.0
                    ))
                jit_book_found = True
            else:
                print(f"  -> NOT FOUND LOCALLY. Searching external APIs for: '{specific_book}'")
                # 2. Use ExternalBookSearch (Google Books -> Open Library -> LLM)
                from app.services.external_search import get_external_search_service
                search_service = get_external_search_service()
                
                # Search using the correct service
                found_books = await search_service.search(specific_book, max_results=1)
                
                if found_books:
                    print(f"  -> External Search SUCCESS. Found: '{found_books[0].title}'")
                    jit_book_found = True
                    
                    # Add found book as candidate
                    candidates.append(RecommendationCandidate(
                        book=found_books[0],
                        similarity_score=2.0,
                        metadata_score=1.0,
                        combined_score=2.0
                    ))
                else:
                    print(f"  -> External Search FAILED. Book not found anywhere.")
        
        # ============ RETRIEVAL: Vector + SQL Fallback ============
        if not jit_book_found:
            query_embedding = await embedding_service.embed_text(optimized_query)
        
            candidates: List[RecommendationCandidate] = await retrieval_service.retrieve(
                query_embedding=query_embedding,
                vector_store=vector_store,
                filters=chat_request.preferences
            )
        
        # SQL FALLBACK: If vector search misses, check the persistent DB
        if not candidates:
            print(f"  -> Vector empty. SQL fallback for: '{optimized_query}'")
            db = get_database()
            sql_results = db.search_books_sql(optimized_query, limit=requested_count)
            
            for row in sql_results:
                try:
                    book = BookInDB(
                        id=row["id"],
                        title=row["title"],
                        author=row["author"],
                        description=row.get("description", ""),
                        genre=row.get("genre", "General"),
                        rating=row.get("rating", 0.0),
                        cover_url=row.get("cover_url"),
                        year_published=row.get("year_published"),
                        is_dynamic=False
                    )
                    candidates.append(RecommendationCandidate(
                        book=book,
                        similarity_score=1.0,
                        metadata_score=1.0,
                        combined_score=1.0
                    ))
                except Exception as e:
                    print(f"  -> SQL->BookInDB error: {e}")
        
        # ============ PERSONAL INTELLIGENCE: Re-score Candidates ============
        if candidates:
            book_ids = [c.book.id for c in candidates]
            scored = pi_service.predict_scores(book_ids, mood)
            
            # Re-order candidates by model scores
            id_to_score = {bid: score for bid, score in scored}
            candidates.sort(key=lambda c: id_to_score.get(c.book.id, 0), reverse=True)
            print(f"  -> Candidates re-ranked by Personal Intelligence Model")
        
        # ============ LAYER 4: NARRATION (Voice Only) ============
        recommendations = await reranking_service.rerank(
            candidates=candidates,
            user_context={
                "message": chat_request.message,
                "emotional_context": mood,
                "personality": personality,
                "user_name": display_name,
                "profile_summary": profile_summary,
                "strategy": strategy  # FROM PERSONAL INTELLIGENCE MODEL
            },
            top_k=requested_count
        )
        
        # Deduplicate
        seen_ids = set()
        unique_recs = []
        for rec in recommendations:
            if rec.book_id not in seen_ids:
                seen_ids.add(rec.book_id)
                unique_recs.append(rec)
        recommendations = unique_recs[:requested_count]
        
        # ============ JIT DESCRIPTION ENRICHMENT (PARALLEL) ============
        from app.services.description import get_description_service
        import asyncio
        
        desc_service = get_description_service()
        enrich_tasks = []
        
        # Identify books needing enrichment
        for rec in recommendations:
            if not rec.description or len(rec.description) < 30:
                enrich_tasks.append(
                    desc_service.get_or_generate(
                        book_id=rec.book_id,
                        title=rec.title,
                        author=rec.author,
                        genre=rec.genre
                    )
                )
            else:
                enrich_tasks.append(None) # Placeholders to match index
        
        # Run all requests in parallel
        if any(t is not None for t in enrich_tasks):
            print(f"  -> Enriching {len([t for t in enrich_tasks if t])} descriptions in parallel...")
            results = await asyncio.gather(*[t for t in enrich_tasks if t is not None], return_exceptions=True)
            
            # Map results back to recommendations
            result_idx = 0
            for i, task in enumerate(enrich_tasks):
                if task is not None:
                    desc = results[result_idx]
                    result_idx += 1
                    
                    if isinstance(desc, str):
                        recommendations[i].description = desc
                    else:
                        print(f"  -> Enrichment error for {recommendations[i].title}: {desc}")
        
        # If specific book requested but not found, try JIT
        if specific_book and not any(specific_book.lower() in r.title.lower() for r in recommendations):
            print(f"  -> Specific '{specific_book}' not found. Triggering JIT...")
            recommendations = await _jit_search(
                request, chat_request.message, requested_count, 
                reranking_service, personality, display_name
            )
            if recommendations:
                message = generate_persona_message(personality, len(recommendations))
                save_to_history(user_id, session_id, "assistant", message)
                return ChatResponse(
                    message=message,
                    recommendations=recommendations,
                    query_understood=True,
                    session_id=session_id
                )
        
        # If still empty, use LLM knowledge fallback
        if not recommendations:
            print("  -> No results. Using LLM knowledge fallback...")
            fallback_text = await reranking_service.generate_from_knowledge(
                user_message=chat_request.message,
                personality=personality,
                user_name=display_name
            )
            save_to_history(user_id, session_id, "assistant", fallback_text)
            return ChatResponse(
                message=fallback_text,
                recommendations=[],
                query_understood=True,
                session_id=session_id
            )
        
        # Success: Generate persona message
        message = generate_persona_message(personality, len(recommendations))
        save_to_history(user_id, session_id, "assistant", message)
        
        return ChatResponse(
            message=message,
            recommendations=recommendations,
            query_understood=True,
            session_id=session_id
        )
        
    except Exception as e:
        print(f"[Chat] Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


async def _jit_search(
    request: Request,
    user_message: str,
    count: int,
    reranking_service: RerankingService,
    personality: str,
    user_name: str
) -> List[RecommendationResult]:
    """JIT (Just-In-Time) search using external APIs when local DB fails."""
    try:
        from app.services.external_search import get_external_search_service
        
        embedding_service = request.app.state.embedding_service
        vector_store = request.app.state.vector_store
        db = get_database()
        
        external_search = get_external_search_service()
        dynamic_books = await external_search.search(query=user_message, max_results=count)
        
        if not dynamic_books:
            return []
        
        results = []
        for book in dynamic_books:
            # Persist to SQLite
            db.add_book({
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "description": book.description,
                "genre": book.genre,
                "rating": book.rating,
                "cover_url": book.cover_url,
                "source": "google_books" if not book.is_dynamic else "ai_generated"
            })
            
            # Add to FAISS for future searches
            book_text = f"{book.title} by {book.author}. {book.description}"
            book_embedding = await embedding_service.embed_text(book_text)
            await vector_store.add_book_dynamic(book, book_embedding)
            
            results.append(RecommendationResult(
                book_id=book.id,
                title=book.title,
                author=book.author,
                description=book.description,
                genre=book.genre,
                rating=book.rating,
                cover_url=book.cover_url,
                explanation=f"Found this one for you! {book.description[:100]}...",
                rank=len(results) + 1
            ))
        
        return results
        
    except Exception as e:
        print(f"[JIT Search] Error: {e}")
        return []


@router.post("/stream")
async def get_recommendations_stream(chat_request: ChatRequest):
    """Streaming endpoint placeholder."""
    raise NotImplementedError("Streaming not yet implemented")
