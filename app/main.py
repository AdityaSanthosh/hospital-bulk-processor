"""FastAPI application with API versioning"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import hospitals
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"API v1 prefix: {settings.api_v1_prefix}")
    logger.info(f"Hospital API: {settings.hospital_api_base_url}")
    logger.info(f"Celery broker: {settings.celery_broker_url}")
    logger.info(f"Rate limit: {settings.rate_limit_requests} req/{settings.rate_limit_period}s")
    logger.info(f"Retry attempts: {settings.retry_max_attempts}")
    logger.info(f"Circuit breaker threshold: {settings.circuit_breaker_failure_threshold}")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Production-ready API for bulk processing hospital records with Celery, rate limiting, circuit breakers, and idempotency",
    version=settings.app_version,
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 router
app.include_router(
    hospitals.router,
    prefix=f"{settings.api_v1_prefix}/hospitals",
    tags=["hospitals"]
)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "api_v1_prefix": settings.api_v1_prefix,
        "status": "running",
        "features": {
            "celery_processing": True,
            "rate_limiting": True,
            "circuit_breaker": True,
            "retry_mechanism": True,
            "idempotency": True,
            "api_versioning": True,
        },
        "endpoints": {
            "docs": f"{settings.api_v1_prefix}/docs",
            "redoc": f"{settings.api_v1_prefix}/redoc",
            "bulk_upload": f"{settings.api_v1_prefix}/hospitals/bulk",
            "job_status": f"{settings.api_v1_prefix}/hospitals/status/{{job_id}}",
            "health": "/health",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "hospital_api_url": settings.hospital_api_base_url,
        "celery_broker": settings.celery_broker_url,
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom exception handler for HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_type": "validation_error" if exc.status_code == 400 else "server_error",
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler for unexpected errors"""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"An unexpected error occurred: {str(exc)}",
            "error_type": "internal_error",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
