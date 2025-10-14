"""FastAPI application for Cerberus Agent."""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest
from starlette.responses import Response

from cerberus_agent.api.routes import agent, health, guardrails, threat_assessment
from cerberus_agent.core.config import get_settings
from cerberus_agent.core.logging import setup_logging

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    setup_logging()
    logger.info("Starting Cerberus Agent API")
    yield
    # Shutdown
    logger.info("Shutting down Cerberus Agent API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    # Prometheus metrics will be added later
    
    app = FastAPI(
        title="Cerberus Agent API",
        description="AI Agent with OpenAI integration and guardrail functionality",
        version="0.1.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # Middleware
    allowed_origins = ["*"] if settings.ALLOWED_ORIGINS == "*" else [settings.ALLOWED_ORIGINS]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    if settings.ALLOWED_HOSTS and settings.ALLOWED_HOSTS != "*":
        allowed_hosts = [settings.ALLOWED_HOSTS] if isinstance(settings.ALLOWED_HOSTS, str) else settings.ALLOWED_HOSTS
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts
        )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Metrics will be added later
        
        logger.info(
            "Request processed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=process_time,
            client_ip=request.client.host if request.client else None,
        )
        
        return response

    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code}
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception",
            exception=str(exc),
            path=request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "status_code": 500}
        )

    # Include routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(agent.router, prefix="/api/v1/agent", tags=["agent"])
    app.include_router(guardrails.router, prefix="/api/v1/guardrails", tags=["guardrails"])
    app.include_router(threat_assessment.router, prefix="/api/v1/threat-assessment", tags=["threat-assessment"])

    # Metrics endpoint
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(generate_latest(), media_type="text/plain")

    return app


app = create_app()

if __name__ == "__main__":
    import time
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "cerberus_agent.api.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )
