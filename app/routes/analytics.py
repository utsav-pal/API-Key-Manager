"""
Analytics routes for usage and audit data.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.user import User
from app.models.api import Api
from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.models.usage import UsageRecord
from app.schemas import UsageStats, AuditLogResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/v1", tags=["Analytics"])


@router.get("/keys/{key_id}/usage", response_model=UsageStats)
async def get_key_usage(
    key_id: str,
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get usage statistics for an API key.
    
    - **days**: Number of days to look back (1-90)
    """
    # Verify key belongs to user
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
    
    # Calculate date range
    since = datetime.utcnow() - timedelta(days=days)
    
    # Get usage stats
    total_result = await db.execute(
        select(func.count(UsageRecord.id))
        .where(UsageRecord.api_key_id == key_id, UsageRecord.created_at >= since)
    )
    total = total_result.scalar() or 0
    
    success_result = await db.execute(
        select(func.count(UsageRecord.id))
        .where(
            UsageRecord.api_key_id == key_id,
            UsageRecord.created_at >= since,
            UsageRecord.status_code < 400
        )
    )
    successful = success_result.scalar() or 0
    
    avg_result = await db.execute(
        select(func.avg(UsageRecord.response_time_ms))
        .where(UsageRecord.api_key_id == key_id, UsageRecord.created_at >= since)
    )
    avg_response = avg_result.scalar()
    
    return UsageStats(
        total_requests=total,
        successful_requests=successful,
        failed_requests=total - successful,
        avg_response_time_ms=round(avg_response, 2) if avg_response else None
    )


@router.get("/keys/{key_id}/audit", response_model=List[AuditLogResponse])
async def get_key_audit_log(
    key_id: str,
    limit: int = Query(50, ge=1, le=500),
    action: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit logs for an API key.
    
    - **limit**: Maximum number of entries (1-500)
    - **action**: Filter by action type (create, verify, revoke, rotate, update)
    """
    # Verify key belongs to user
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
    
    # Build query
    query = select(AuditLog).where(AuditLog.api_key_id == key_id)
    
    if action:
        query = query.where(AuditLog.action == action)
    
    query = query.order_by(AuditLog.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/apis/{api_id}/analytics", response_model=dict)
async def get_api_analytics(
    api_id: str,
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated analytics for all keys in an API.
    """
    # Verify API belongs to user
    result = await db.execute(
        select(Api).where(Api.id == api_id, Api.owner_id == current_user.id)
    )
    api = result.scalar_one_or_none()
    
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API not found"
        )
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # Count keys
    keys_result = await db.execute(
        select(func.count(ApiKey.id)).where(ApiKey.api_id == api_id)
    )
    total_keys = keys_result.scalar() or 0
    
    active_keys_result = await db.execute(
        select(func.count(ApiKey.id))
        .where(ApiKey.api_id == api_id, ApiKey.revoked == False)
    )
    active_keys = active_keys_result.scalar() or 0
    
    # Total verifications
    verifications_result = await db.execute(
        select(func.count(AuditLog.id))
        .join(ApiKey)
        .where(
            ApiKey.api_id == api_id,
            AuditLog.action == "verify",
            AuditLog.created_at >= since
        )
    )
    total_verifications = verifications_result.scalar() or 0
    
    return {
        "api_id": api_id,
        "api_name": api.name,
        "period_days": days,
        "total_keys": total_keys,
        "active_keys": active_keys,
        "revoked_keys": total_keys - active_keys,
        "total_verifications": total_verifications
    }
