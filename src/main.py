"""
PostSync FastAPI Application Entry Point

This module initializes and configures the FastAPI application with all routes,
middleware, and dependencies.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api import analytics, auth, content, users
from src.config.settings import get_settings
from src.utils.logger import setup_logging
from src.utils.monitoring import performance_monitor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    setup_logging()
    logger = structlog.get_logger(__name__)
    logger.info("PostSync application starting up")
    
    yield
    
    # Shutdown
    logger.info("PostSync application shutting down")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="PostSync API",
        description="AI-powered social media automation for AI professionals",
        version="1.0.0",
        docs_url="/docs" if settings.environment == "development" else None,
        redoc_url="/redoc" if settings.environment == "development" else None,
        lifespan=lifespan,
    )
    
    # Add performance monitoring middleware
    @app.middleware("http")
    async def monitor_requests(request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        process_time = time.time() - start_time
        
        # Track API performance
        await performance_monitor.track_api_performance(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            response_time=process_time
        )
        
        # Add performance headers
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routers
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    app.include_router(content.router, prefix="/api/v1/content", tags=["content"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
    
    # Mount static files for frontend
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
    
    return app


# Create the application instance
app = create_application()


@app.get("/")
async def root():
    """Root endpoint with basic application information."""
    return {
        "name": "PostSync API",
        "version": "1.0.0",
        "description": "AI-powered social media automation for AI professionals",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    health_data = await performance_monitor.get_system_health()
    
    return {
        "status": health_data.get("status", "healthy"),
        "service": "postsync-api",
        "version": "1.0.0",
        "timestamp": health_data.get("timestamp"),
        "uptime_percentage": health_data.get("uptime_percentage"),
        "active_alerts": health_data.get("active_alerts", 0)
    }


@app.get("/metrics")
async def get_metrics():
    """Get system metrics for monitoring dashboard."""
    return await performance_monitor.get_system_health()


@app.get("/performance-report")
async def get_performance_report(hours: int = 24):
    """Get detailed performance report."""
    return await performance_monitor.get_performance_report(hours_back=hours)


@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, acknowledged_by: str = "api_user"):
    """Acknowledge a system alert."""
    success = await performance_monitor.acknowledge_alert(alert_id, acknowledged_by)
    
    if success:
        return {"message": f"Alert {alert_id} acknowledged"}
    else:
        return {"error": f"Alert {alert_id} not found"}, 404


@app.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, resolved_by: str = "api_user"):
    """Mark a system alert as resolved."""
    success = await performance_monitor.resolve_alert(alert_id, resolved_by)
    
    if success:
        return {"message": f"Alert {alert_id} resolved"}
    else:
        return {"error": f"Alert {alert_id} not found"}, 404


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger = structlog.get_logger(__name__)
    logger.error(
        "Unhandled exception occurred",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )