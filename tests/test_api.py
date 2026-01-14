"""
API integration tests.
"""
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Test root endpoint."""
    response = await client.get("/")
    
    assert response.status_code == 200
    assert "name" in response.json()


@pytest.mark.asyncio
async def test_register_user(client):
    """Test user registration."""
    response = await client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "password123"}
    )
    
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Test duplicate email registration fails."""
    # First registration
    await client.post(
        "/auth/register",
        json={"email": "dupe@example.com", "password": "password123"}
    )
    
    # Duplicate
    response = await client.post(
        "/auth/register",
        json={"email": "dupe@example.com", "password": "password123"}
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login(client):
    """Test user login."""
    # Register
    await client.post(
        "/auth/register",
        json={"email": "login@example.com", "password": "password123"}
    )
    
    # Login
    response = await client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "password123"}
    )
    
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_invalid(client):
    """Test invalid login fails."""
    response = await client.post(
        "/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"}
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_api(client, auth_headers):
    """Test API creation."""
    response = await client.post(
        "/v1/apis",
        headers=auth_headers,
        json={"name": "My API"}
    )
    
    assert response.status_code == 201
    assert response.json()["name"] == "My API"


@pytest.mark.asyncio
async def test_list_apis(client, auth_headers, test_api):
    """Test listing APIs."""
    response = await client.get("/v1/apis", headers=auth_headers)
    
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_create_key(client, auth_headers, test_api):
    """Test API key creation."""
    response = await client.post(
        "/v1/keys",
        headers=auth_headers,
        json={
            "api_id": test_api["id"],
            "name": "Test Key"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "key" in data  # Raw key returned once
    assert data["key"].startswith("sk_live_")


@pytest.mark.asyncio
async def test_list_keys(client, auth_headers, test_api):
    """Test listing keys."""
    # Create a key first
    await client.post(
        "/v1/keys",
        headers=auth_headers,
        json={"api_id": test_api["id"], "name": "Key 1"}
    )
    
    response = await client.get("/v1/keys", headers=auth_headers)
    
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_verify_key_not_found(client):
    """Test verifying non-existent key."""
    response = await client.post(
        "/v1/keys/verify",
        json={"key": "sk_live_nonexistent"}
    )
    
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["error"] == "Key not found"


@pytest.mark.asyncio
async def test_revoke_key(client, auth_headers, test_api):
    """Test key revocation."""
    # Create key
    create_response = await client.post(
        "/v1/keys",
        headers=auth_headers,
        json={"api_id": test_api["id"]}
    )
    key_id = create_response.json()["id"]
    
    # Revoke
    response = await client.delete(
        f"/v1/keys/{key_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_protection(client, auth_headers, test_api):
    """Test delete protection prevents deletion."""
    # Create key with protection
    create_response = await client.post(
        "/v1/keys",
        headers=auth_headers,
        json={
            "api_id": test_api["id"],
            "delete_protection": True
        }
    )
    key_id = create_response.json()["id"]
    
    # Try to delete without force
    response = await client.delete(
        f"/v1/keys/{key_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 400
    
    # Delete with force
    response = await client.delete(
        f"/v1/keys/{key_id}?force=true",
        headers=auth_headers
    )
    
    assert response.status_code == 204
