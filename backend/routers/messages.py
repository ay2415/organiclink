"""
Messaging router for OrganicLink.
Supports messages to registered users OR pitch messages to seeded directory hubs.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from database import get_db
from models import User, Message, HubDirectory
from schemas.schemas import MessageCreate, MessageResponse
from routers.auth import get_current_user

router = APIRouter(prefix="/api/messages", tags=["Messages"])


@router.post("", response_model=MessageResponse)
def send_message(
    msg_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not msg_in.recipient_id and not msg_in.hub_directory_id:
        raise HTTPException(status_code=400, detail="Must specify recipient_id or hub_directory_id")

    msg = Message(
        sender_id=current_user.id,
        recipient_id=msg_in.recipient_id,
        hub_directory_id=msg_in.hub_directory_id,
        order_id=msg_in.order_id,
        product_id=msg_in.product_id,
        message_text=msg_in.message_text
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return build_message_response(msg, db)


@router.get("/conversations")
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    messages = db.query(Message).filter(
        or_(Message.sender_id == current_user.id, Message.recipient_id == current_user.id)
    ).order_by(Message.created_at.desc()).all()

    # Group by conversation partner / hub
    convs = {}
    for m in messages:
        if m.sender_id == current_user.id:
            key = m.recipient_id or f"hub_{m.hub_directory_id}"
        else:
            key = m.sender_id

        if key not in convs:
            convs[key] = build_message_response(m, db)

    return list(convs.values())


@router.get("/thread/{partner_id}")
def get_message_thread(
    partner_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if partner_id.startswith("hub_"):
        hub_id = partner_id.replace("hub_", "")
        messages = db.query(Message).filter(
            Message.sender_id == current_user.id,
            Message.hub_directory_id == hub_id
        ).order_by(Message.created_at.asc()).all()
    else:
        messages = db.query(Message).filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.recipient_id == partner_id),
                and_(Message.sender_id == partner_id, Message.recipient_id == current_user.id)
            )
        ).order_by(Message.created_at.asc()).all()

    return [build_message_response(m, db) for m in messages]


@router.put("/{message_id}/read")
def mark_message_read(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.read_at = datetime.utcnow()
    db.commit()
    return {"message": "Message marked read"}


def build_message_response(msg: Message, db: Session) -> MessageResponse:
    sender = db.query(User).filter(User.id == msg.sender_id).first()
    recipient = db.query(User).filter(User.id == msg.recipient_id).first() if msg.recipient_id else None
    hub = db.query(HubDirectory).filter(HubDirectory.id == msg.hub_directory_id).first() if msg.hub_directory_id else None

    res = MessageResponse.model_validate(msg)
    res.sender_name = sender.name if sender else "Sender"
    res.recipient_name = recipient.name if recipient else None
    res.hub_name = hub.name if hub else None
    return res
