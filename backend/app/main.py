"""
FastAPI Application Entry Point

This module initializes the FastAPI application with:
- CORS middleware for frontend communication
- Lifespan handlers for startup/shutdown (vector DB, model loading)
- API router mounting with versioning
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import get_settings
from app.db.vector_store import VectorStore
from app.services.embedding import EmbeddingService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for application startup and shutdown.
    
    Startup:
    - Initialize embedding model (lazy loading for faster cold starts)
    - Load or create FAISS index
    
    Shutdown:
    - Persist FAISS index to disk
    - Clean up resources
    """
    settings = get_settings()
    
    # --- STARTUP ---
    print(f"Starting {settings.app_name}...")
    
    # Initialize services and store in app.state for access in routes
    # Using lazy initialization - models load on first use
    app.state.embedding_service = EmbeddingService()
    app.state.vector_store = VectorStore()
    
    # Attempt to load existing FAISS index
    await app.state.vector_store.initialize()
    
    print("Application started successfully")
    
    yield  # Application runs here
    
    # --- SHUTDOWN ---
    print("Shutting down application...")
    
    # Persist vector store to disk
    await app.state.vector_store.persist()
    
    print("Shutdown complete")


def create_application() -> FastAPI:
    """
    Application factory pattern.
    
    Benefits:
    - Easier testing (can create fresh app instances)
    - Clear separation of configuration from instantiation
    - Consistent setup across different environments
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        description=(
            "A personalized book recommendation API using the Retrieve & Rerank "
            "architecture. Combines vector similarity search with LLM-powered "
            "contextual explanations for deeply personalized recommendations."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # CORS Configuration
    # In production, replace "*" with specific frontend origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount API router with version prefix
    app.include_router(
        api_router,
        prefix=settings.api_v1_prefix
    )
    
    # Mount Static Files (Frontend)
    from fastapi.staticfiles import StaticFiles
    from pathlib import Path
    
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
    else:
        print("Static folder not found. Frontend will not be served.")
    
    return app


# Create the application instance
app = create_application()
