from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import inspect, text
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

REQUIRED_SCHEMA_TABLES = {
    "users",
    "workspaces",
    "workspace_members",
    "instagram_accounts",
    "instagram_data_deletion_requests",
    "automations",
    "reel_analysis_jobs",
    "reel_reports",
}


def verify_database_schema_ready(db_engine) -> None:
    """
    Verifies connectivity and required schema/migration state.
    In staging, production, or PostgreSQL environments, requires Alembic migration tracking
    and core tables instead of silently auto-creating un-migrated tables.
    """
    env_name = (settings.ENVIRONMENT or "development").lower()
    strict_migration_check = db_engine.dialect.name != "sqlite" or env_name in ("staging", "production")

    with db_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        if strict_migration_check:
            inspector = inspect(conn)
            existing_tables = set(inspector.get_table_names())
            if "alembic_version" not in existing_tables:
                raise RuntimeError(
                    "Database schema is not migrated (missing alembic_version). Run 'alembic upgrade head' before starting."
                )
            applied_rev = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
            if not applied_rev:
                raise RuntimeError(
                    "Database migration state is empty in alembic_version. Run 'alembic upgrade head' before starting."
                )
            missing_tables = sorted(REQUIRED_SCHEMA_TABLES - existing_tables)
            if missing_tables:
                raise RuntimeError(
                    f"Database schema is missing expected migrated tables: {', '.join(missing_tables)}"
                )


# Only auto-create SQLite tables in local dev convenience mode; never mask migrations in staging/production/PostgreSQL
if (settings.ENVIRONMENT or "development").lower() in ("development", "local") and engine.dialect.name == "sqlite":
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    env_name = (settings.ENVIRONMENT or "development").lower()
    if engine.dialect.name != "sqlite" or env_name in ("staging", "production"):
        verify_database_schema_ready(engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Woka — Creator Economy SaaS, Instagram Automation & Brand Collaboration API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
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
    allow_credentials=True if "*" not in settings.CORS_ORIGINS else False,
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
    """Standard container readiness probe verifying database connectivity and migrated schema."""
    try:
        verify_database_schema_ready(engine)
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
            detail=f"Database readiness check failed ({type(exc).__name__}): {str(exc)}"
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

