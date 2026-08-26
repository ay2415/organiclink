"""
Reputation & Trust Engine for OrganicLink Marketplace.

Computes multi-criteria composite farm reputation score (0-100) following completed transactions.
Incorporates star ratings, automated CV quality consistency, fulfillment timeliness, and dispute rates.

Weighting Breakdown:
- 0.40 * Mean Buyer Star Ratings (scaled 0-100)
- 0.30 * Mean Computer Vision Quality Score across verified completed orders
- 0.20 * On-Time Delivery Fulfillment Rate (100 - dispute penalty)
- 0.10 * Dispute-Free Transaction Ratio

References:
- Jøsang, A., Ismail, R., & Boyd, C. (2007). A survey of trust and reputation systems for online service provision. Decision Support Systems, 43(2), 618-644.
- Dellarocas, C. (2003). The digitization of word of mouth: Promise and challenges of online feedback mechanisms. Management Science, 49(10), 1407-1424.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Farm, Order, RatingReview, QualityInspection


def update_farm_reputation(db: Session, farm_id: str, *args, **kwargs) -> float:
    """
    Recalculates composite reputation score for a farm and persists to database.
    """
    farm = db.query(Farm).filter((Farm.id == farm_id) | (Farm.user_id == farm_id)).first()
    if not farm:
        return 0.0

    # 1. Mean Star Ratings (1-5 scale normalized to 0-100)
    reviews = db.query(RatingReview).filter(RatingReview.ratee_id == farm.user_id).all()
    if reviews:
        mean_stars = sum(r.rating_stars for r in reviews) / len(reviews)
        star_component = (mean_stars / 5.0) * 100.0
    else:
        star_component = 85.0 # Benchmark initial rating for newly verified organic producers

    # 2. Mean Computer-Vision Quality Score across completed orders
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

    # 3. Fulfillment reliability & dispute penalty calculation
    all_farm_orders = db.query(Order).filter(Order.farmer_id == farm.user_id).all()
    if all_farm_orders:
        disputed_count = sum(1 for o in all_farm_orders if o.dispute_flag)
        dispute_rate = disputed_count / len(all_farm_orders)
        on_time_rate = max(0.0, 1.0 - (dispute_rate * 0.5))
    else:
        dispute_rate = 0.0
        on_time_rate = 1.0

    ontime_component = on_time_rate * 100.0
    dispute_component = max(0.0, 100.0 - (dispute_rate * 100.0))

    # Multi-factor composite weighting
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
