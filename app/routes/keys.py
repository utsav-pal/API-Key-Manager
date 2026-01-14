"""
API Keys routes - the core of the system.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.redis import get_redis
from app.models.user import User
from app.models.api import Api
from app.models.api_key import ApiKey
from app.schemas import (
    KeyCreate, KeyCreateResponse, KeyResponse, KeyUpdate,
    KeyVerifyRequest, KeyVerifyResponse
)
from app.dependencies import get_current_user
from app.services.hashing import generate_api_key, hash_api_key
from app.services.rate_limiter import RateLimiter, UsageLimiter
from app.services.audit import AuditService
from app.utils.ip_utils import is_ip_allowed
from app.config import settings

router = APIRouter(prefix="/v1/keys", tags=["API Keys"])


@router.post("", response_model=KeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    data: KeyCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API key.
    
    The raw key is returned ONLY ONCE in this response.
    Store it securely - it cannot be retrieved again.
    """
    # Verify API belongs to user
    result = await db.execute(
        select(Api).where(Api.id == data.api_id, Api.owner_id == current_user.id)
    )
    api = result.scalar_one_or_none()
    
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API not found"
        )
    
    # Generate key
    raw_key, key_hash, key_prefix = generate_api_key()
    
    # Create key record
    api_key = ApiKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=data.name,
        api_id=data.api_id,
        owner_id=data.owner_id,
        meta=data.metadata or {},
        allowed_ips=data.allowed_ips or [],
        rate_limit_max=data.rate_limit_max or settings.DEFAULT_RATE_LIMIT,
        rate_limit_window=data.rate_limit_window or settings.DEFAULT_RATE_LIMIT_WINDOW,
        remaining_uses=data.remaining_uses,
        max_uses=data.remaining_uses,
        refill_enabled=data.refill_enabled,
        refill_amount=data.refill_amount,
        refill_interval=data.refill_interval,
        expires_at=data.expires_at,
        delete_protection=data.delete_protection
    )
    
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)
    
    # Create audit log
    await AuditService.log(
        db=db,
        api_key_id=str(api_key.id),
        action="create",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return KeyCreateResponse(
        id=api_key.id,
        key=raw_key,  # Shown only once!
        key_prefix=key_prefix,
        name=api_key.name,
        api_id=api_key.api_id,
        created_at=api_key.created_at
    )


@router.get("", response_model=List[KeyResponse])
async def list_keys(
    api_id: Optional[str] = None,
    owner_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List API keys for the current user's APIs.
    
    - **api_id**: Filter by specific API
    - **owner_id**: Filter by owner association
    """
    # Get user's APIs
    query = select(ApiKey).join(Api).where(Api.owner_id == current_user.id)
    
    if api_id:
        query = query.where(ApiKey.api_id == api_id)
    if owner_id:
        query = query.where(ApiKey.owner_id == owner_id)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{key_id}", response_model=KeyResponse)
async def get_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific API key by ID."""
    result = await db.execute(
        select(ApiKey)
        .join(Api)
        .where(ApiKey.id == key_id, Api.owner_id == current_user.id)
    )
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found"
        )
    
    return key


@router.patch("/{key_id}", response_model=KeyResponse)
async def update_key(
    key_id: str,
    data: KeyUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an API key's settings."""
    result = await db.execute(
        select(ApiKey)
        .join(Api)
        .where(ApiKey.id == key_id, Api.owner_id == current_user.id)
    )
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found"
        )
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(key, field, value)
    
    # Audit log
    await AuditService.log(
        db=db,
        api_key_id=str(key.id),
        action="update",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        context={"updated_fields": list(update_data.keys())}
    )
    
    await db.flush()
    await db.refresh(key)
    
    return key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(
    key_id: str,
    force: bool = False,
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Revoke an API key.
    
    - **force**: Override delete protection
    """
    result = await db.execute(
        select(ApiKey)
        .join(Api)
        .where(ApiKey.id == key_id, Api.owner_id == current_user.id)
    )
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found"
        )
    
    # Check delete protection
    if key.delete_protection and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Key has delete protection. Use force=true to override."
        )
    
    # Revoke key
    key.revoked = True
    key.revoked_at = datetime.utcnow()
    
    # Audit log
    await AuditService.log(
        db=db,
        api_key_id=str(key.id),
        action="revoke",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent") if request else None
    )


@router.post("/{key_id}/rotate", response_model=KeyCreateResponse)
async def rotate_key(
    key_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Rotate an API key - revokes old key and creates new one with same settings.
    
    New key is returned ONLY ONCE.
    """
    result = await db.execute(
        select(ApiKey)
        .join(Api)
        .where(ApiKey.id == key_id, Api.owner_id == current_user.id)
    )
    old_key = result.scalar_one_or_none()
    
    if not old_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Key not found"
        )
    
    # Generate new key
    raw_key, key_hash, key_prefix = generate_api_key()
    
    # Create new key with same settings
    new_key = ApiKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=old_key.name,
        api_id=old_key.api_id,
        owner_id=old_key.owner_id,
        meta=old_key.meta,
        allowed_ips=old_key.allowed_ips,
        rate_limit_max=old_key.rate_limit_max,
        rate_limit_window=old_key.rate_limit_window,
        remaining_uses=old_key.max_uses,  # Reset to original max
        max_uses=old_key.max_uses,
        refill_enabled=old_key.refill_enabled,
        refill_amount=old_key.refill_amount,
        refill_interval=old_key.refill_interval,
        expires_at=old_key.expires_at,
        delete_protection=old_key.delete_protection
    )
    
    # Revoke old key
    old_key.revoked = True
    old_key.revoked_at = datetime.utcnow()
    
    db.add(new_key)
    await db.flush()
    await db.refresh(new_key)
    
    # Audit logs
    await AuditService.log(
        db=db,
        api_key_id=str(old_key.id),
        action="rotate_old",
        ip_address=request.client.host if request.client else None,
        context={"new_key_id": str(new_key.id)}
    )
    
    await AuditService.log(
        db=db,
        api_key_id=str(new_key.id),
        action="rotate_new",
        ip_address=request.client.host if request.client else None,
        context={"old_key_id": str(old_key.id)}
    )
    
    return KeyCreateResponse(
        id=new_key.id,
        key=raw_key,
        key_prefix=key_prefix,
        name=new_key.name,
        api_id=new_key.api_id,
        created_at=new_key.created_at
    )


@router.post("/verify", response_model=KeyVerifyResponse)
async def verify_key(
    data: KeyVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify an API key.
    
    This endpoint:
    1. Validates the key exists and is not revoked/expired
    2. Checks IP whitelist
    3. Checks rate limit
    4. Decrements usage limit
    5. Logs the verification
    
    Returns key metadata and rate limit info if valid.
    """
    # Hash the provided key
    key_hash = hash_api_key(data.key)
    
    # Find key by hash
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash)
    )
    api_key = result.scalar_one_or_none()
    
    # Key not found
    if not api_key:
        return KeyVerifyResponse(valid=False, error="Key not found")
    
    # Check if revoked
    if api_key.revoked:
        await _log_verify(db, api_key, request, False, "revoked")
        return KeyVerifyResponse(valid=False, error="Key revoked")
    
    # Check expiration
    if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
        await _log_verify(db, api_key, request, False, "expired")
        return KeyVerifyResponse(valid=False, error="Key expired")
    
    # Check IP whitelist
    client_ip = request.client.host if request.client else None
    if not is_ip_allowed(client_ip, api_key.allowed_ips):
        await _log_verify(db, api_key, request, False, "ip_blocked")
        return KeyVerifyResponse(valid=False, error="IP not allowed")
    
    # Check rate limit
    remaining = None
    reset_at = None
    
    if api_key.rate_limit_max:
        redis_client = await get_redis()
        rate_limiter = RateLimiter(redis_client)
        
        allowed, remaining, reset_at = await rate_limiter.check_rate_limit(
            key_id=str(api_key.id),
            max_requests=api_key.rate_limit_max,
            window_seconds=api_key.rate_limit_window or 3600
        )
        
        if not allowed:
            await _log_verify(db, api_key, request, False, "rate_limited")
            return KeyVerifyResponse(
                valid=False,
                error="Rate limit exceeded",
                remaining=0,
                reset_at=reset_at
            )
    
    # Check usage limit
    if api_key.remaining_uses is not None:
        allowed, new_remaining = await UsageLimiter.check_and_decrement(
            key_id=str(api_key.id),
            remaining=api_key.remaining_uses,
            max_uses=api_key.max_uses
        )
        
        if not allowed:
            await _log_verify(db, api_key, request, False, "usage_exceeded")
            return KeyVerifyResponse(valid=False, error="Usage limit exceeded")
        
        # Update remaining uses
        api_key.remaining_uses = new_remaining
    
    # Update last used
    api_key.last_used_at = datetime.utcnow()
    
    # Log successful verification
    await _log_verify(db, api_key, request, True, None)
    
    return KeyVerifyResponse(
        valid=True,
        key_id=api_key.id,
        owner_id=api_key.owner_id,
        metadata=api_key.meta,
        remaining=remaining,
        reset_at=reset_at
    )


async def _log_verify(
    db: AsyncSession,
    api_key: ApiKey,
    request: Request,
    success: bool,
    reason: Optional[str]
):
    """Helper to log verification attempts."""
    await AuditService.log(
        db=db,
        api_key_id=str(api_key.id),
        action="verify",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        context={"success": success, "reason": reason}
    )
