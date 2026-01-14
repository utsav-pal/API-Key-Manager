"""
Audit log model for tracking all key actions.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.uuid_type import UUID


class AuditLog(Base):
    """
    Audit log for tracking API key actions.
    Actions: create, verify, revoke, rotate, update, delete
    """
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    api_key_id = Column(UUID, ForeignKey("api_keys.id"), nullable=False)
    
    # Action details
    action = Column(String(50), nullable=False)  # create, verify, revoke, rotate, update
    
    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Additional context
    context = Column(JSON, default=dict)  # Any extra info
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    api_key = relationship("ApiKey", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog {self.action} at {self.created_at}>"
