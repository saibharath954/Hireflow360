"""
Audit logging utilities
"""

from datetime import datetime
from sqlalchemy.orm import Session
import uuid

from app.models.models import AuditLog

def _to_uuid(value):
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))

def audit_log(
    db: Session,
    user_id=None,
    action: str = "",
    resource_type: str = "",
    resource_id=None,
    details: dict = None,
    ip_address: str = None,
    user_agent: str = None
):
    """
    Create an audit log entry
    """
    try:
        log_entry = AuditLog(
            id=uuid.uuid4(),
            user_id=_to_uuid(user_id),
            action=action,
            resource_type=resource_type,
            resource_id=_to_uuid(resource_id),
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        print(f"Audit logging failed: {str(e)}")
        db.rollback()
