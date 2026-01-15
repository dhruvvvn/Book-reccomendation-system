"""
Configuration Management

Uses Pydantic Settings for type-safe environment variable handling.
All configuration is centralized here to ensure single source of truth.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Pydantic Settings automatically reads from .env file and environment.
    Field names are case-insensitive for env vars.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra env vars not defined here
    )
    
    # Application Settings
    app_name: str = "BookRecommendationAPI"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    
    # Database (PostgreSQL) - Optional for initial scaffold
    database_url: Optional[str] = None
    
    # Vector Store Configuration
    faiss_index_path: str = "./data/faiss_index"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384  # Dimension for all-MiniLM-L6-v2
    
    # Gemini API
    gemini_api_key: Optional[str] = None
    
    # Retrieval Settings
    top_k_candidates: int = 20  # Number of candidates from vector search
    top_k_results: int = 5      # Final recommendations after reranking
    min_similarity_score: float = 0.1  # Lowered for synthetic descriptions
    
    # Cache Settings
    cache_ttl_seconds: int = 3600  # 1 hour default TTL
    cache_max_size: int = 1000     # Max cached items


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance.
    
    Using lru_cache ensures settings are loaded once and reused,
    avoiding repeated file I/O and parsing on every request.
    """
    return Settings()
