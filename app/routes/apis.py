"""
APIs routes (multi-tenant namespaces).
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.api import Api
from app.schemas import ApiCreate, ApiResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/v1/apis", tags=["APIs"])


@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_api(
    data: ApiCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new API namespace.
    
    APIs are containers for API keys. Each user can have multiple APIs.
    """
    api = Api(
        name=data.name,
        owner_id=current_user.id
    )
    
    db.add(api)
    await db.flush()
    await db.refresh(api)
    
    return api


@router.get("", response_model=List[ApiResponse])
async def list_apis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all APIs owned by the current user.
    """
    result = await db.execute(
        select(Api).where(Api.owner_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/{api_id}", response_model=ApiResponse)
async def get_api(
    api_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific API by ID.
    """
    result = await db.execute(
        select(Api).where(Api.id == api_id, Api.owner_id == current_user.id)
    )
    api = result.scalar_one_or_none()
    
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API not found"
        )
    
    return api


@router.delete("/{api_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api(
    api_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an API and all its keys.
    
    This will permanently delete all API keys in this namespace.
    """
    result = await db.execute(
        select(Api).where(Api.id == api_id, Api.owner_id == current_user.id)
    )
    api = result.scalar_one_or_none()
    
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API not found"
        )
    
    await db.delete(api)
