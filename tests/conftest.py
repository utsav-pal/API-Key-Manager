"""
Pytest configuration and fixtures.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event
from unittest.mock import AsyncMock, patch
from app.main import app
from app.database import Base, get_db
from app.config import settings

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_db():
    """Create test database and tables."""
    # Create engine with SQLite-compatible settings
    engine = create_async_engine(
        TEST_DATABASE_URL, 
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    # Enable foreign key support for SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async def override_get_db():
        async with async_session() as session:
            yield session
    
    # Mock Redis for testing
    mock_redis = AsyncMock()
    mock_redis.pipeline.return_value = mock_redis
    mock_redis.zremrangebyscore = AsyncMock()
    mock_redis.zcard = AsyncMock(return_value=0)
    mock_redis.zadd = AsyncMock()
    mock_redis.expire = AsyncMock()
    mock_redis.execute = AsyncMock(return_value=[None, 0, None, None])
    mock_redis.zrem = AsyncMock()
    
    async def mock_get_redis():
        return mock_redis
    
    app.dependency_overrides[get_db] = override_get_db
    
    with patch('app.routes.keys.get_redis', mock_get_redis):
        yield async_session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(test_db):
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_token(client):
    """Get authentication token for tests."""
    # Register user
    await client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "testpassword123"}
    )
    
    # Login
    response = await client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"}
    )
    
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token):
    """Get authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def test_api(client, auth_headers):
    """Create a test API."""
    response = await client.post(
        "/v1/apis",
        headers=auth_headers,
        json={"name": "Test API"}
    )
    return response.json()
