"""
Authentication Endpoints

Simple username/password authentication for user accounts.
No email verification - just signup and login.
"""

import json
from fastapi import APIRouter, HTTPException, Request

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


# ============ READING LIST ENDPOINTS ============

from pydantic import BaseModel

class ReadingListRequest(BaseModel):
    book_id: str


class ReadingListResponse(BaseModel):
    success: bool
    message: str
    reading_list: list = []


@router.post("/user/{user_id}/reading-list", response_model=ReadingListResponse)
async def add_to_reading_list(user_id: int, request: ReadingListRequest) -> ReadingListResponse:
    """Add a book to user's reading list."""
    db = get_database()
    
    user = db.get_user(user_id)
    if not user:
        return ReadingListResponse(success=False, message="User not found")
    
    # Check if already in list
    existing = db.get_user_interactions(user_id, action="reading_list", limit=1000)
    if any(i["book_id"] == request.book_id for i in existing):
        return ReadingListResponse(
            success=False, 
            message="Book already in your reading list",
            reading_list=[i["book_id"] for i in existing]
        )
    
    # Add to list using interactions table
    db.log_interaction(user_id, request.book_id, "reading_list")
    
    # Return updated list
    updated = db.get_user_interactions(user_id, action="reading_list", limit=1000)
    return ReadingListResponse(
        success=True,
        message="Book added to reading list!",
        reading_list=[i["book_id"] for i in updated]
    )


@router.get("/user/{user_id}/reading-list", response_model=ReadingListResponse)
async def get_reading_list(
    request: Request,
    user_id: int
) -> ReadingListResponse:
    """Get user's reading list with full book details."""
    from app.api.v1.endpoints.discover import _book_to_dict
    
    db = get_database()
    
    user = db.get_user(user_id)
    if not user:
        return ReadingListResponse(success=False, message="User not found")
    
    # Get IDs from DB
    items = db.get_user_interactions(user_id, action="reading_list", limit=1000)
    book_ids = [i["book_id"] for i in items]
    
    # Resolve to full books from Vector Store
    vector_store = request.app.state.vector_store
    full_books = []
    
    for bib in book_ids:
        # Try finding by string ID or int ID
        book = None
        if bib in vector_store._books:
            book = vector_store._books[bib]
        elif str(bib).isdigit() and int(bib) in vector_store._books:
            book = vector_store._books[int(bib)]
        else:
            # Linear scan fallback (slow but safe)
            for b in vector_store._books.values():
                if str(b.id) == str(bib):
                    book = b
                    break
        
        if book:
            full_books.append(_book_to_dict(book))
            
    return ReadingListResponse(
        success=True,
        message=f"Found {len(full_books)} books",
        reading_list=full_books
    )


@router.delete("/user/{user_id}/reading-list/{book_id}")
async def remove_from_reading_list(user_id: int, book_id: str) -> ReadingListResponse:
    """Remove a book from user's reading list."""
    db = get_database()
    
    user = db.get_user(user_id)
    if not user:
        return ReadingListResponse(success=False, message="User not found")
    
    # Delete from interactions table
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM interactions WHERE user_id = ? AND book_id = ? AND action = 'reading_list'",
        (user_id, book_id)
    )
    conn.commit()
    conn.close()
    
    # Return updated list
    items = db.get_user_interactions(user_id, action="reading_list", limit=1000)
    return ReadingListResponse(
        success=True,
        message="Book removed from reading list",
        reading_list=[i["book_id"] for i in items]
    )
