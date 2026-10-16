from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.config import settings
from app.database import Base, engine
import app.models  # Ensures all models are imported and registered with Base.metadata

from app.routers import (
    auth,
    instagram,
    automations,
    analytics,
    ai_studio,
    media_kit,
    campaigns,
    invoices,
    subscriptions,
    notifications,
    admin,
    reel_intelligence
)

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Woka — Creator Economy SaaS, Instagram Automation & Brand Collaboration API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc"
)

# Configure Trusted Hosts Protection
if settings.ALLOWED_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(instagram.router, prefix=settings.API_V1_STR)
app.include_router(automations.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)
app.include_router(ai_studio.router, prefix=settings.API_V1_STR)
app.include_router(media_kit.router, prefix=settings.API_V1_STR)
app.include_router(campaigns.router, prefix=settings.API_V1_STR)
app.include_router(invoices.router, prefix=settings.API_V1_STR)
app.include_router(subscriptions.router, prefix=settings.API_V1_STR)
app.include_router(notifications.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)
app.include_router(reel_intelligence.router, prefix=settings.API_V1_STR)

@app.get("/healthz", tags=["Health"])
def liveness_probe():
    """Standard container liveness probe."""
    return {"status": "alive"}

@app.get("/readyz", tags=["Health"])
def readiness_probe():
    """Standard container readiness probe verifying database connectivity."""
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT
        }
    except Exception as exc:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database readiness check failed: {str(exc)}"
        )

@app.get("/api/health", tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }

@app.get("/", tags=["Health"])
def root():
    return {
        "message": "Welcome to Woka API. Visit /api/v1/docs for OpenAPI documentation.",
        "status": "operational"
    }

