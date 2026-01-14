"""
Usage record model for analytics.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database import Base
from app.utils.uuid_type import UUID


class UsageRecord(Base):
    """Usage record for tracking API requests."""
    
    __tablename__ = "usage_records"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    api_key_id = Column(UUID, ForeignKey("api_keys.id"), nullable=False)
    
    # Request details
    endpoint = Column(String(500), nullable=True)
    method = Column(String(10), nullable=True)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    api_key = relationship("ApiKey", back_populates="usage_records")
    
    def __repr__(self):
        return f"<UsageRecord {self.endpoint} at {self.created_at}>"
