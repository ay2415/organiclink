"""
Demand scoring router for OrganicLink.
Exposes hybrid activity vs seasonal demand indicator.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from services.demand import get_product_demand

router = APIRouter(prefix="/api/demand", tags=["Demand Scoring"])


@router.get("")
def get_demand_indicator(
    product_type: str = Query("onion"),
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return get_product_demand(db, product_type=product_type, county=county)
