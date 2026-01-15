"""
Chat Endpoint

Main conversational interface for book recommendations.
Accepts user messages and returns personalized book recommendations
with empathetic, context-aware explanations.

Architecture Note:
This endpoint orchestrates the full Retrieve & Rerank flow:
1. Embed user query
2. Retrieve candidates from vector store
3. Rerank with LLM and generate explanations
4. Return structured response
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from typing import List
import traceback

from app.models.chat import ChatRequest, ChatResponse
from app.models.recommendation import RecommendationResult
from app.services.retrieval import RetrievalService, get_retrieval_service
from app.services.reranking import RerankingService, get_reranking_service

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def get_recommendations(
    request: Request,
    chat_request: ChatRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    reranking_service: RerankingService = Depends(get_reranking_service)
) -> ChatResponse:
    """
    Process user message and return personalized book recommendations.
    
    Flow:
    1. Extract user intent and context from message
    2. Generate embedding for semantic search
    3. Retrieve top-k candidates using hybrid search
    4. Rerank candidates with LLM considering user context
    5. Generate empathetic explanations for each recommendation
    
    Args:
        chat_request: User message with optional context/preferences
        retrieval_service: Injected retrieval service
        reranking_service: Injected reranking service
    
    Returns:
        ChatResponse with ranked recommendations and explanations
    """
    try:
        # Get embedding service from app state
        embedding_service = request.app.state.embedding_service
        vector_store = request.app.state.vector_store
        
        # Step 1: Generate query embedding
        query_embedding = await embedding_service.embed_text(chat_request.message)
        
        # Step 2: Retrieve candidates using hybrid search
        candidates = await retrieval_service.retrieve(
            query_embedding=query_embedding,
            vector_store=vector_store,
            filters=chat_request.preferences
        )
        
        # Step 3: Rerank with LLM and generate explanations
        recommendations: List[RecommendationResult] = await reranking_service.rerank(
            candidates=candidates,
            user_context={
                "message": chat_request.message,
                "preferences": chat_request.preferences,
                "emotional_context": chat_request.emotional_context
            }
        )
        
        # Generate personality-aware response message
        is_friendly = chat_request.emotional_context == "casual"
        
        if not recommendations:
            if is_friendly:
                message = "Hmm, I couldn't find any books matching that exactly 🤔 Try describing what you're in the mood for!"
            else:
                message = "I couldn't find books matching your query. Please try a different search term or describe your preferences."
        else:
            if is_friendly:
                message = f"Found some amazing reads for you! 📚✨ Here are {len(recommendations)} books I think you'll love:"
            else:
                message = f"Based on your query, I have identified {len(recommendations)} relevant recommendations for your consideration:"
        
        return ChatResponse(
            message=message,
            recommendations=recommendations,
            query_understood=True
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
    # Placeholder for SSE implementation
    raise NotImplementedError("Streaming not yet implemented")
