"""Health check endpoints."""

import time
from typing import Dict, Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from cerberus_agent.core.config import get_settings
from cerberus_agent.core.config import Settings

logger = structlog.get_logger(__name__)
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: float
    version: str
    environment: str
    uptime: float


class DetailedHealthResponse(HealthResponse):
    """Detailed health check response model."""
    dependencies: Dict[str, Any]
    system_info: Dict[str, Any]


@router.get("/", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=time.time(),
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        uptime=time.time() - settings.START_TIME,
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(settings: Settings = Depends(get_settings)) -> DetailedHealthResponse:
    """Detailed health check with dependency status."""
    dependencies = {
        "openai": await _check_openai_connection(),
        "redis": await _check_redis_connection(),
        "database": await _check_database_connection(),
    }
    
    system_info = {
        "python_version": settings.PYTHON_VERSION,
        "platform": settings.PLATFORM,
        "memory_usage": _get_memory_usage(),
    }
    
    return DetailedHealthResponse(
        status="healthy" if all(dependencies.values()) else "degraded",
        timestamp=time.time(),
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        uptime=time.time() - settings.START_TIME,
        dependencies=dependencies,
        system_info=system_info,
    )


async def _check_openai_connection() -> bool:
    """Check OpenAI API connection."""
    try:
        # Add actual OpenAI connection check here
        return True
    except Exception as e:
        logger.warning("OpenAI connection check failed", error=str(e))
        return False


async def _check_redis_connection() -> bool:
    """Check Redis connection."""
    try:
        # Add actual Redis connection check here
        return True
    except Exception as e:
        logger.warning("Redis connection check failed", error=str(e))
        return False


async def _check_database_connection() -> bool:
    """Check database connection."""
    try:
        # Add actual database connection check here
        return True
    except Exception as e:
        logger.warning("Database connection check failed", error=str(e))
        return False


def _get_memory_usage() -> Dict[str, Any]:
    """Get current memory usage information."""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "rss": memory_info.rss,
            "vms": memory_info.vms,
            "percent": process.memory_percent(),
        }
    except ImportError:
        return {"error": "psutil not available"}
    except Exception as e:
        return {"error": str(e)}
