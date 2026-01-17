"""
Chat Pydantic Models

Request and response schemas for the conversational interface.
Designed to capture user context including emotional state and preferences
to enable deeply personalized recommendations.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.models.recommendation import RecommendationResult


class UserPreferences(BaseModel):
    """
    User preferences for filtering and personalization.
    
    These are explicit preferences that can be used for
    metadata filtering during retrieval.
    """
    favorite_genres: Optional[List[str]] = Field(
        None,
        description="Genres the user enjoys"
    )
    disliked_genres: Optional[List[str]] = Field(
        None,
        description="Genres to avoid"
    )
    min_rating: Optional[float] = Field(
        None,
        ge=0,
        le=5,
        description="Minimum acceptable rating"
    )
    preferred_length: Optional[str] = Field(
        None,
        description="Preferred book length: 'short', 'medium', 'long'"
    )


class ChatRequest(BaseModel):
    """
    Chat request from the user.
    
    The message is the primary input, but additional context
    can be provided to improve recommendation quality.
    
    If user_id is provided, the assistant loads the user's personality
    preference and chat history from the database.
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's message/query"
    )
    user_id: Optional[int] = Field(
        None,
        description="User ID for personalization and persistent memory"
    )
    preferences: Optional[UserPreferences] = Field(
        None,
        description="Explicit user preferences for filtering"
    )
    emotional_context: Optional[str] = Field(
        None,
        max_length=500,
        description="User's current emotional state or life context"
    )
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None,
        description="Previous messages for multi-turn context"
    )
    session_id: Optional[str] = Field(
        None,
        description="Session identifier for conversation continuity"
    )


class ChatResponse(BaseModel):
    """
    Chat response with recommendations.
    
    Contains both a conversational message and structured
    recommendation data for rendering book cards.
    """
    message: str = Field(
        ...,
        description="Conversational response text"
    )
    recommendations: List[RecommendationResult] = Field(
        default_factory=list,
        description="Ranked book recommendations with explanations"
    )
    query_understood: bool = Field(
        True,
        description="Whether the query was successfully interpreted"
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for conversation continuity"
    )
    follow_up_questions: Optional[List[str]] = Field(
        None,
        description="Suggested follow-up questions for the user"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata (timing, candidate count, etc.)"
    )

