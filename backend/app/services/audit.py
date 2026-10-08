from typing import Optional

from sqlalchemy.orm import Session

from ..models import AuditLog
from ..security import Principal


def log(db: Session, user: Optional[Principal], action: str, entity_type: Optional[str] = None,
        entity_id: Optional[int] = None, details: Optional[str] = None) -> None:
    """Adds an audit row to the caller's transaction (committed together with the change)."""
    db.add(AuditLog(
        action=action, entity_type=entity_type, entity_id=entity_id,
        details=details[:1000] if details else details,
        user_id=user.id if user else None, username=user.username if user else None,
        ip_address=user.ip if user else None))


def log_as(db: Session, user_id: Optional[int], username: Optional[str], action: str,
           entity_type: Optional[str] = None, entity_id: Optional[int] = None,
           details: Optional[str] = None, ip: Optional[str] = None) -> None:
    db.add(AuditLog(user_id=user_id, username=username, action=action, entity_type=entity_type,
                    entity_id=entity_id, details=details[:1000] if details else details, ip_address=ip))
