"""
Authentication Endpoints

Simple username/password authentication for user accounts.
No email verification - just signup and login.
"""

import json
from fastapi import APIRouter, HTTPException

from app.models.user import (
    UserSignup, UserLogin, UserPreferences,
    UserResponse, AuthResponse
)
from app.db.database import get_database

router = APIRouter()


def _user_to_response(user_dict: dict) -> UserResponse:
    """Convert database user dict to response model."""
    genres = user_dict.get("favorite_genres", "[]")
    if isinstance(genres, str):
        genres = json.loads(genres)
    
    return UserResponse(
        id=user_dict["id"],
        username=user_dict["username"],
        display_name=user_dict.get("display_name") or user_dict["username"],
        theme=user_dict.get("theme", "dark"),
        personality=user_dict.get("personality", "friendly"),
        favorite_genres=genres
    )


@router.post("/signup", response_model=AuthResponse)
async def signup(request: UserSignup) -> AuthResponse:
    """
    Create a new user account.
    
    Returns success with user data, or error if username taken.
    """
    db = get_database()
    
    user_id = db.create_user(
        username=request.username,
        password=request.password,
        display_name=request.display_name
    )
    
    if user_id is None:
        return AuthResponse(
            success=False,
            message="Username already taken"
        )
    
    user = db.get_user(user_id)
    return AuthResponse(
        success=True,
        message="Account created successfully!",
        user=_user_to_response(user)
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: UserLogin) -> AuthResponse:
    """
    Authenticate existing user.
    
    Returns success with user data, or error if credentials invalid.
    """
    db = get_database()
    
    user = db.authenticate_user(request.username, request.password)
    
    if user is None:
        return AuthResponse(
            success=False,
            message="Invalid username or password"
        )
    
    return AuthResponse(
        success=True,
        message=f"Welcome back, {user.get('display_name', user['username'])}!",
        user=_user_to_response(user)
    )


@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(user_id: int) -> UserResponse:
    """Get user by ID."""
    db = get_database()
    user = db.get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return _user_to_response(user)


@router.put("/user/{user_id}/preferences", response_model=UserResponse)
async def update_preferences(user_id: int, preferences: UserPreferences) -> UserResponse:
    """Update user preferences (theme, personality, genres)."""
    db = get_database()
    
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.update_user_preferences(
        user_id=user_id,
        theme=preferences.theme,
        personality=preferences.personality,
        favorite_genres=preferences.favorite_genres
    )
    
    updated_user = db.get_user(user_id)
    return _user_to_response(updated_user)
