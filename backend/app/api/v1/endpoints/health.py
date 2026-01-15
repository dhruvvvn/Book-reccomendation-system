"""
Health Check Endpoint

Provides a simple health check for monitoring and load balancers.
Useful for Kubernetes probes, Docker health checks, and uptime monitoring.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health_check() -> dict:
    """
    Health check endpoint.
    
    Returns:
        Basic health status. Can be extended to check DB connections,
        external service availability, etc.
    """
    return {
        "status": "healthy",
        "service": "book-recommendation-api",
        "version": "0.1.0"
    }


@router.get("/ready")
async def readiness_check() -> dict:
    """
    Readiness probe endpoint.
    
    Indicates whether the service is ready to accept traffic.
    Differs from health in that it may check if required services
    (DB, vector store, ML model) are loaded and ready.
    """
    # TODO: Add actual readiness checks
    # - Check if FAISS index is loaded
    # - Check if embedding model is loaded
    # - Check PostgreSQL connection
    return {
        "ready": True,
        "checks": {
            "vector_store": "ok",
            "embedding_model": "ok",
            "database": "ok"
        }
    }
