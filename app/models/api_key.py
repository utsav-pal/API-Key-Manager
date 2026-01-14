"""
API Key model - the core of the system.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.uuid_type import UUID


class ApiKey(Base):
    """
    API Key with full Unkey-like features.
    
    SECURITY: Raw key is NEVER stored. Only key_hash is persisted.
    """
    
    __tablename__ = "api_keys"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    
    # Key identification (hash only, never raw key)
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)  # e.g., "sk_live_abc..."
    
    # Basic info
    name = Column(String(255), nullable=True)
    api_id = Column(UUID, ForeignKey("apis.id"), nullable=False)
    
    # Owner association (link key to external user)
    owner_id = Column(String(255), nullable=True, index=True)
    
    # Custom metadata
    meta = Column(JSON, default=dict)
    
    # IP Whitelisting
    allowed_ips = Column(JSON, default=list)  # ["192.168.1.0/24", "10.0.0.1"]
    
    # Rate limiting
    rate_limit_max = Column(Integer, nullable=True)  # max requests
    rate_limit_window = Column(Integer, nullable=True)  # window in seconds
    
    # Usage limits
    remaining_uses = Column(Integer, nullable=True)  # decrements each use
    max_uses = Column(Integer, nullable=True)  # original limit
    refill_enabled = Column(Boolean, default=False)
    refill_amount = Column(Integer, nullable=True)
    refill_interval = Column(Integer, nullable=True)  # seconds
    last_refill_at = Column(DateTime, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    
    # Status
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)
    
    # Delete protection
    delete_protection = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationships
    api = relationship("Api", back_populates="keys")
    audit_logs = relationship("AuditLog", back_populates="api_key", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="api_key", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ApiKey {self.key_prefix}...>"
    
    @property
    def is_valid(self) -> bool:
        """Check if key is still valid."""
        if self.revoked:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        if self.remaining_uses is not None and self.remaining_uses <= 0:
            return False
        return True
