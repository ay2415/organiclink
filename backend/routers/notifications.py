"""
Notifications router for OrganicLink.
"""

from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, Notification
from schemas.schemas import NotificationResponse
from routers.auth import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
def get_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).all()


@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    noti = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if not noti:
        raise HTTPException(status_code=404, detail="Notification not found")

    noti.read_at = datetime.utcnow()
    db.commit()
    return {"message": "Notification marked as read"}
