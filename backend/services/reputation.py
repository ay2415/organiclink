"""
Reputation engine for OrganicLink farms.
Recomputes farm reputation_score (0-100) after every completed order.
Formula:
0.40 * mean(star ratings * 20)
+ 0.30 * mean(farm quality_scores across completed orders)
+ 0.20 * (on-time delivery rate * 100)
+ 0.10 * (100 - dispute rate * 100)
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Farm, Order, RatingReview, QualityInspection


def update_farm_reputation(db: Session, farm_id: str, *args, **kwargs) -> float:
    farm = db.query(Farm).filter((Farm.id == farm_id) | (Farm.user_id == farm_id)).first()
    if not farm:
        return 0.0

    # 1. Mean Star Ratings (1-5 scaled to 0-100)
    reviews = db.query(RatingReview).filter(RatingReview.ratee_id == farm.user_id).all()
    if reviews:
        mean_stars = sum(r.rating_stars for r in reviews) / len(reviews)
        star_component = (mean_stars / 5.0) * 100.0
    else:
        star_component = 85.0 # default for new farms

    # 2. Mean Farm Quality Score across completed orders
    completed_orders = db.query(Order).filter(
        Order.farmer_id == farm.user_id,
        Order.status.in_(["delivered", "paid", "completed"])
    ).all()

    farm.total_orders_completed = len(completed_orders)

    quality_scores = []
    for ord_obj in completed_orders:
        if ord_obj.farm_inspection_id:
            insp = db.query(QualityInspection).filter(QualityInspection.id == ord_obj.farm_inspection_id).first()
            if insp:
                quality_scores.append(insp.quality_score)

    if quality_scores:
        mean_quality = sum(quality_scores) / len(quality_scores)
        farm.average_quality_score = round(mean_quality, 1)
    else:
        mean_quality = farm.average_quality_score or 85.0

    # 3. On-time delivery rate (percentage of orders completed without dispute)
    all_farm_orders = db.query(Order).filter(Order.farmer_id == farm.user_id).all()
    if all_farm_orders:
        disputed_count = sum(1 for o in all_farm_orders if o.dispute_flag)
        dispute_rate = disputed_count / len(all_farm_orders)
        on_time_rate = 1.0 - (dispute_rate * 0.5) # proxy
    else:
        dispute_rate = 0.0
        on_time_rate = 1.0

    ontime_component = on_time_rate * 100.0
    dispute_component = max(0.0, 100.0 - (dispute_rate * 100.0))

    # Calculate weighted reputation score
    reputation_score = (
        0.40 * star_component +
        0.30 * mean_quality +
        0.20 * ontime_component +
        0.10 * dispute_component
    )

    farm.reputation_score = round(max(0.0, min(100.0, reputation_score)), 1)
    db.commit()
    db.refresh(farm)
    return farm.reputation_score
