"""
Regional Produce Demand Estimation Service for OrganicLink.

Computes 30-day trailing demand indicators across regional markets based on
order velocity, active buyer inquiries, and contract allocations.

References:
- Box, G. E., Jenkins, G. M., Reinsel, G. C., & Ljung, G. M. (2015). Time Series Analysis: Forecasting and Control. John Wiley & Sons.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import Order, Product, ProductType


def get_regional_demand_indicators(db: Session, county: str = None) -> list:
    """
    Aggregates regional demand metrics across product categories over a 30-day window.
    """
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    query = db.query(
        Product.title,
        Product.category,
        func.count(Order.id).label("order_count"),
        func.sum(Order.quantity).label("total_volume")
    ).outerjoin(Order, Order.product_id == Product.id)     .filter(Order.created_at >= thirty_days_ago)

    if county:
        query = query.filter(Product.origin_county == county)

    results = query.group_by(Product.title, Product.category).all()
    
    indicators = []
    for r in results:
        volume = float(r.total_volume or 0)
        # Classify demand intensity
        if volume > 500:
            level = "high"
        elif volume > 100:
            level = "medium"
        else:
            level = "steady"
            
        indicators.append({
            "product_title": r.title,
            "category": r.category,
            "order_count_30d": r.order_count,
            "volume_kg_30d": volume,
            "demand_level": level
        })
        
    return indicators
