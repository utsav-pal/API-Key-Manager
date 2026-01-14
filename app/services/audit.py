"""
Audit logging service.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


class AuditService:
    """Service for creating audit logs."""
    
    @staticmethod
    async def log(
        db: AsyncSession,
        api_key_id: str,
        action: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        context: Optional[dict] = None
    ) -> AuditLog:
        """
        Create an audit log entry.
        
        Args:
            db: Database session
            api_key_id: The API key ID
            action: Action type (create, verify, revoke, rotate, update, delete)
            ip_address: Client IP address
            user_agent: Client user agent
            context: Additional context data
            
        Returns:
            AuditLog: The created audit log entry
        """
        audit_log = AuditLog(
            api_key_id=api_key_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            context=context or {}
        )
        
        db.add(audit_log)
        await db.flush()
        
        return audit_log
