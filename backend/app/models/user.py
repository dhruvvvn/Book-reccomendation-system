"""
User Pydantic Models

Request and response schemas for user authentication and preferences.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class UserSignup(BaseModel):
    """Signup request."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4)
    display_name: Optional[str] = None


class UserLogin(BaseModel):
    """Login request."""
    username: str
    password: str


class UserPreferences(BaseModel):
    """User preference update request."""
    theme: Optional[str] = Field(None, pattern="^(dark|light)$")
    personality: Optional[str] = Field(None, pattern="^(formal|friendly)$")
    favorite_genres: Optional[List[str]] = None


class UserResponse(BaseModel):
    """User data response (excludes password)."""
    id: int
    username: str
    display_name: str
    theme: str
    personality: str
    favorite_genres: List[str] = []


class AuthResponse(BaseModel):
    """Authentication response."""
    success: bool
    message: str
    user: Optional[UserResponse] = None
