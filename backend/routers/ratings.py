"""
Ratings, reviews, and farm reputation trigger router for OrganicLink.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import User, RatingReview, Order, Farm
from schemas.schemas import RatingCreate, RatingResponse
from routers.auth import get_current_user
from services.reputation import update_farm_reputation
from services.audit import log_audit_event

router = APIRouter(prefix="/api", tags=["Ratings & Reputation"])


@router.post("/ratings", response_model=RatingResponse)
def submit_rating(
    rating_in: RatingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == rating_in.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.id not in [order.farmer_id, order.buyer_id] and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to rate this transaction")

    existing = db.query(RatingReview).filter(
        RatingReview.order_id == rating_in.order_id,
        RatingReview.rater_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already rated this order")

    rating = RatingReview(
        order_id=rating_in.order_id,
        rater_id=current_user.id,
        ratee_id=rating_in.ratee_id,
        rating_stars=rating_in.rating_stars,
        quality_consistency=rating_in.quality_consistency,
        timeliness=rating_in.timeliness,
        communication=rating_in.communication,
        reliability=rating_in.reliability,
        review_text=rating_in.review_text
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)

    # Check if both parties have rated -> mark completed
    all_ratings = db.query(RatingReview).filter(RatingReview.order_id == order.id).all()
    if len(all_ratings) >= 2 or order.status == "paid":
        order.status = "completed"
        db.commit()

    # Recompute farm reputation score
    farm = db.query(Farm).filter(Farm.user_id == rating_in.ratee_id).first()
    if not farm:
        farm = db.query(Farm).filter(Farm.user_id == order.farmer_id).first()
    if farm:
        update_farm_reputation(db, farm.id)

    log_audit_event(db, action="rating_submitted", actor_id=current_user.id, actor_role=current_user.role, order_id=order.id, details={"stars": rating_in.rating_stars})
    return rating


@router.get("/farms/{farm_id}/ratings")
def get_farm_ratings(farm_id: str, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    reviews = db.query(RatingReview).filter(RatingReview.ratee_id == farm.user_id).order_by(RatingReview.created_at.desc()).all()
    return reviews


@router.get("/users/{user_id}/reputation")
def get_user_reputation(user_id: str, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.user_id == user_id).first()
    if farm:
        return {
            "user_id": user_id,
            "farm_id": farm.id,
            "reputation_score": farm.reputation_score,
            "total_orders_completed": farm.total_orders_completed,
            "average_quality_score": farm.average_quality_score
        }
    return {"user_id": user_id, "reputation_score": 85.0, "total_orders_completed": 0}
