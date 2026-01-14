"""Pydantic schemas for API requests/responses."""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


# ==================== Auth Schemas ====================
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== API Schemas ====================
class ApiCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ApiResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Key Schemas ====================
class KeyCreate(BaseModel):
    """Request to create a new API key."""
    api_id: UUID
    name: Optional[str] = None
    owner_id: Optional[str] = None
    metadata: Optional[dict] = None
    allowed_ips: Optional[List[str]] = None
    rate_limit_max: Optional[int] = Field(None, ge=1)
    rate_limit_window: Optional[int] = Field(None, ge=1)  # seconds
    remaining_uses: Optional[int] = Field(None, ge=1)
    refill_enabled: bool = False
    refill_amount: Optional[int] = Field(None, ge=1)
    refill_interval: Optional[int] = Field(None, ge=1)  # seconds
    expires_at: Optional[datetime] = None
    delete_protection: bool = False


class KeyCreateResponse(BaseModel):
    """
    Response after creating a key.
    key is shown ONLY ONCE - must be saved by user.
    """
    id: UUID
    key: str  # Raw key - shown only once!
    key_prefix: str
    name: Optional[str]
    api_id: UUID
    created_at: datetime


class KeyResponse(BaseModel):
    """API key details (without raw key)."""
    id: UUID
    key_prefix: str
    name: Optional[str]
    api_id: UUID
    owner_id: Optional[str]
    metadata: Optional[dict] = Field(None, alias="meta")
    allowed_ips: Optional[List[str]]
    rate_limit_max: Optional[int]
    rate_limit_window: Optional[int]
    remaining_uses: Optional[int]
    max_uses: Optional[int]
    refill_enabled: bool
    expires_at: Optional[datetime]
    revoked: bool
    delete_protection: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    
    class Config:
        from_attributes = True
        populate_by_name = True


class KeyUpdate(BaseModel):
    """Update key settings."""
    name: Optional[str] = None
    owner_id: Optional[str] = None
    metadata: Optional[dict] = None
    allowed_ips: Optional[List[str]] = None
    rate_limit_max: Optional[int] = None
    rate_limit_window: Optional[int] = None
    remaining_uses: Optional[int] = None
    refill_enabled: Optional[bool] = None
    refill_amount: Optional[int] = None
    refill_interval: Optional[int] = None
    expires_at: Optional[datetime] = None
    delete_protection: Optional[bool] = None


class KeyVerifyRequest(BaseModel):
    """Request to verify an API key."""
    key: str


class KeyVerifyResponse(BaseModel):
    """Response from key verification."""
    valid: bool
    key_id: Optional[UUID] = None
    owner_id: Optional[str] = None
    metadata: Optional[dict] = None
    remaining: Optional[int] = None  # Rate limit remaining
    reset_at: Optional[int] = None  # Rate limit reset timestamp
    error: Optional[str] = None


# ==================== Analytics Schemas ====================
class UsageStats(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: Optional[float]


class AuditLogResponse(BaseModel):
    id: UUID
    action: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    context: Optional[dict]
    created_at: datetime
    
    class Config:
        from_attributes = True
