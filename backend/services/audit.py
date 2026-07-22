"""
Audit service for OrganicLink.
Insert-only helper called on every order state transition and system action.
"""

from sqlalchemy.orm import Session
from models import AuditLog


def log_audit_event(
    db: Session,
    action: str,
    actor_id: str = None,
    actor_role: str = None,
    order_id: str = None,
    details: dict = None
) -> AuditLog:
    """
    Creates and records an immutable audit log entry.
    """
    entry = AuditLog(
        order_id=order_id,
        action=action,
        actor_id=actor_id,
        actor_role=actor_role,
        details=details or {}
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
