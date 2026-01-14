"""
API model for multi-tenant key organization.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.uuid_type import UUID


class Api(Base):
    """API namespace that contains multiple keys."""
    
    __tablename__ = "apis"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    owner_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="apis")
    keys = relationship("ApiKey", back_populates="api", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Api {self.name}>"
