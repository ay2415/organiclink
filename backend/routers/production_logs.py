"""
Production Logging Router for OrganicLink (Addendum A3).
Handles Day-wise logging for Milk and Batch-wise logging for Produce.
Calculates net surplus by subtracting active contract commitments.
"""

from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.all_models import ProductionLog, Farm, Contract, User, ProductType
from routers.auth import get_current_user, require_role

router = APIRouter(prefix="/api/production-logs", tags=["Production Logs"])


class ProductionLogCreate(BaseModel):
    product_type: str
    log_type: str = "batch" # daily, batch
    log_date: str # YYYY-MM-DD
    batch_reference: Optional[str] = None
    quantity: float
    unit: str = "kg" # kg, litre
    notes: Optional[str] = None


class DailyBulkItem(BaseModel):
    log_date: str # YYYY-MM-DD
    quantity: float


class DailyBulkCreate(BaseModel):
    product_type: str = "milk"
    unit: str = "litre"
    entries: List[DailyBulkItem]


@router.get("")
def list_production_logs(
    product_type: Optional[str] = Query(None),
    log_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = db.query(Farm).filter(Farm.user_id == current_user.id).first()
    if not farm:
        return []

    query = db.query(ProductionLog).filter(ProductionLog.farm_id == farm.id)
    if product_type:
        query = query.filter(ProductionLog.product_type == product_type.lower())
    if log_type:
        query = query.filter(ProductionLog.log_type == log_type.lower())

    logs = query.order_by(ProductionLog.log_date.desc()).all()
    return logs


@router.post("")
def create_production_log(
    log_in: ProductionLogCreate,
    current_user: User = Depends(require_role(["farmer", "admin"])),
    db: Session = Depends(get_db)
):
    farm = db.query(Farm).filter(Farm.user_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm profile not found. Must be a farmer to log production.")

    log_date_obj = datetime.strptime(log_in.log_date, "%Y-%m-%d").date()

    # Auto generate batch reference if batch log
    batch_ref = log_in.batch_reference
    if log_in.log_type == "batch" and not batch_ref:
        batch_ref = f"{log_in.product_type.upper()}-{log_date_obj.strftime('%Y%m%d')}-A"

    log = ProductionLog(
        farm_id=farm.id,
        product_type=log_in.product_type.lower(),
        log_type=log_in.log_type,
        log_date=log_date_obj,
        batch_reference=batch_ref,
        quantity=log_in.quantity,
        unit=log_in.unit.lower(),
        notes=log_in.notes
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return {"message": "Production log saved successfully", "log": log}


@router.post("/bulk-daily")
def create_bulk_daily_logs(
    bulk_in: DailyBulkCreate,
    current_user: User = Depends(require_role(["farmer", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Allows dairy farmers to type a month of daily milk volumes in a single request.
    """
    farm = db.query(Farm).filter(Farm.user_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm profile not found.")

    created_count = 0
    for item in bulk_in.entries:
        if item.quantity <= 0:
            continue
        log_date_obj = datetime.strptime(item.log_date, "%Y-%m-%d").date()
        
        # Upsert log for that day
        existing = db.query(ProductionLog).filter(
            ProductionLog.farm_id == farm.id,
            ProductionLog.product_type == bulk_in.product_type.lower(),
            ProductionLog.log_date == log_date_obj,
            ProductionLog.log_type == "daily"
        ).first()

        if existing:
            existing.quantity = item.quantity
        else:
            new_log = ProductionLog(
                farm_id=farm.id,
                product_type=bulk_in.product_type.lower(),
                log_type="daily",
                log_date=log_date_obj,
                quantity=item.quantity,
                unit=bulk_in.unit.lower(),
                notes="Bulk daily entry"
            )
            db.add(new_log)
        created_count += 1

    db.commit()
    return {"message": f"Successfully logged {created_count} daily entries for {bulk_in.product_type}."}


@router.get("/surplus")
def get_surplus_calculation(
    product_type: str = Query("milk"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculates surplus = produced quantity - active committed contract quantity.
    Excludes expired contracts.
    """
    farm = db.query(Farm).filter(Farm.user_id == current_user.id).first()
    if not farm:
        return {"produced": 0, "committed": 0, "surplus": 0}

    today = datetime.utcnow().date()
    p_type = product_type.lower()

    # 1. Total produced quantity
    logs = db.query(ProductionLog).filter(
        ProductionLog.farm_id == farm.id,
        ProductionLog.product_type == p_type
    ).all()
    total_produced = sum(l.quantity for l in logs)

    # 2. Active committed contract quantity (exclude expired contracts where end_date < today)
    contracts = db.query(Contract).filter(
        Contract.farm_id == farm.id,
        Contract.product_type == p_type,
        Contract.status == "active"
    ).all()

    total_committed = 0.0
    for c in contracts:
        if c.end_date and c.end_date < today:
            continue # Expired contract (A2)
        
        # Normalise period to total
        qty = c.committed_quantity
        total_committed += qty

    surplus = max(0.0, total_produced - total_committed)

    return {
        "product_type": p_type,
        "total_produced": round(total_produced, 2),
        "total_committed": round(total_committed, 2),
        "surplus": round(surplus, 2),
        "unit": "litre" if p_type == "milk" else "kg"
    }
