"""
API Key Manager - FastAPI Application Entry Point

A self-hosted API key management service with full Unkey.dev-like features.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.redis import close_redis
from app.routes import auth, apis, keys, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_redis()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="""
## API Key Manager

A self-hosted API key management service with full feature parity to Unkey.dev.

### Features

- **Secure Key Hashing** - Keys are hashed with HMAC-SHA256, never stored raw
- **Rate Limiting** - Redis-based sliding window rate limiting per key
- **Usage Limits** - Limit total uses with optional auto-refill
- **IP Whitelisting** - Restrict keys to specific IPs or CIDRs
- **Audit Logs** - Track all key actions
- **Key Rotation** - Seamlessly rotate keys
- **Delete Protection** - Prevent accidental deletion

### Quick Start

1. Register at `/auth/register`
2. Login at `/auth/login` to get JWT token
3. Create an API at `/v1/apis`
4. Create keys at `/v1/keys`
5. Verify keys at `/v1/keys/verify`
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth.router)
app.include_router(apis.router)
app.include_router(keys.router)
app.include_router(analytics.router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Railway deployment."""
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
