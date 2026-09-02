"""
Admin administration router for OrganicLink.
Farm verification queue, dispute resolution queue, audit log viewer, platform metrics, and system settings.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, Farm, Order, QualityInspection, Payment, AuditLog, AdminSetting
from schemas.schemas import (
    AdminFarmVerify, OrderDisputeResolve, AdminSettingsUpdate, FarmResponse, OrderResponse
)
from routers.auth import require_role
from services.audit import log_audit_event
from services.reputation import update_farm_reputation
from config import settings

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/farms", response_model=List[FarmResponse])
def get_farms_queue(
    verified: Optional[bool] = Query(False),
    admin_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    query = db.query(Farm)
    if verified is not None:
        query = query.filter(Farm.verified == verified)
    return query.order_by(Farm.created_at.desc()).all()


@router.put("/farms/{farm_id}/verify", response_model=FarmResponse)
def verify_farm(
    farm_id: str,
    verify_in: AdminFarmVerify,
    admin_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    farm.verified = verify_in.verified
    if verify_in.verified:
        farm.verification_status = "verified"
        if farm.owner:
            farm.owner.verified = True
            farm.owner.status = "verified"
    else:
        farm.verification_status = "rejected"
        if farm.owner:
            farm.owner.verified = False
            farm.owner.status = "rejected"
    db.commit()

    log_audit_event(
        db, action="farm_verified" if verify_in.verified else "farm_unverified",
        actor_id=admin_user.id, actor_role="admin", details={"farm_id": farm.id, "note": verify_in.note}
    )
    return farm


@router.get("/disputes")
def list_disputes(
    status: Optional[str] = Query("open"),
    admin_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    query = db.query(Order).filter(Order.dispute_flag == True)
    if status:
        query = query.filter(Order.dispute_status == status)

    disputed_orders = query.order_by(Order.updated_at.desc()).all()

    results = []
    for o in disputed_orders:
        farm_insp = db.query(QualityInspection).filter(QualityInspection.id == o.farm_inspection_id).first() if o.farm_inspection_id else None
        deliv_insp = db.query(QualityInspection).filter(QualityInspection.id == o.delivery_inspection_id).first() if o.delivery_inspection_id else None
        farmer = db.query(User).filter(User.id == o.farmer_id).first()
        buyer = db.query(User).filter(User.id == o.buyer_id).first()
        payment = db.query(Payment).filter(Payment.order_id == o.id).first()

        results.append({
            "order_id": o.id,
            "product_type": o.product.product_type if o.product else "Produce",
            "farmer": {"id": farmer.id, "name": farmer.name} if farmer else None,
            "buyer": {"id": buyer.id, "name": buyer.name, "role": buyer.role} if buyer else None,
            "quantity": o.quantity,
            "quantity_unit": o.quantity_unit,
            "total_price": o.total_price,
            "dispute_reason": o.dispute_reason,
            "dispute_status": o.dispute_status,
            "dispute_resolution": o.dispute_resolution,
            "dispute_rationale": o.dispute_rationale,
            "quality_variance_percent": o.quality_variance_percent,
            "farm_inspection": {
                "id": farm_insp.id if farm_insp else None,
                "score": farm_insp.quality_score if farm_insp else None,
                "grade": farm_insp.quality_grade if farm_insp else None,
                "image_url": farm_insp.image_url if farm_insp else None,
                "defects": farm_insp.defects_detected if farm_insp else []
            },
            "delivery_inspection": {
                "id": deliv_insp.id if deliv_insp else None,
                "score": deliv_insp.quality_score if deliv_insp else None,
                "grade": deliv_insp.quality_grade if deliv_insp else None,
                "image_url": deliv_insp.image_url if deliv_insp else None,
                "defects": deliv_insp.defects_detected if deliv_insp else []
            },
            "payment_status": payment.status if payment else "held",
            "created_at": o.created_at
        })

    return results


@router.put("/disputes/{order_id}/resolve")
def resolve_dispute(
    order_id: str,
    resolve_in: OrderDisputeResolve,
    admin_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    valid_resolutions = ["full_payment", "partial_payment", "refund_buyer", "dismiss"]
    if resolve_in.resolution not in valid_resolutions:
        raise HTTPException(status_code=400, detail=f"Invalid resolution type. Must be one of {valid_resolutions}")

    order.dispute_status = "resolved" if resolve_in.resolution != "dismiss" else "dismissed"
    order.dispute_resolution = resolve_in.resolution
    order.dispute_rationale = resolve_in.rationale
    if resolve_in.resolution == "dismiss":
        order.dispute_flag = False
        order.status = "paid"
    else:
        order.status = "paid" if resolve_in.resolution in ["full_payment", "partial_payment"] else "delivered"

    payment = db.query(Payment).filter(Payment.order_id == order.id).first()
    if payment:
        if resolve_in.resolution in ["full_payment", "dismiss"]:
            payment.status = "paid"
            payment.paid_date = datetime.utcnow().date()
        elif resolve_in.resolution == "partial_payment":
            pct = resolve_in.partial_percent or 50.0
            payment.amount = round(order.total_price * (pct / 100.0), 2)
            payment.status = "partial"
            payment.paid_date = datetime.utcnow().date()
        else: # refund_buyer
            payment.status = "refunded"

    db.commit()

    log_audit_event(
        db, action="dispute_resolved" if resolve_in.resolution != "dismiss" else "dispute_dismissed",
        actor_id=admin_user.id, actor_role="admin",
        order_id=order.id, details={"resolution": resolve_in.resolution, "rationale": resolve_in.rationale, "partial_percent": resolve_in.partial_percent}
    )

    # Update farm reputation
    farm = db.query(Farm).filter(Farm.user_id == order.farmer_id).first()
    if farm:
        update_farm_reputation(db, farm.id)

    return {
        "message": f"Dispute resolved with resolution '{resolve_in.resolution}'",
        "order_id": order.id,
        "dispute_status": order.dispute_status,
        "payment_status": payment.status if payment else None
    }


@router.put("/disputes/{order_id}/dismiss")
def dismiss_dispute(
    order_id: str,
    admin_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Admin dismisses a flagged dispute.
    Unflags the order, marks dispute as dismissed, and releases payment to farmer.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.dispute_flag = False
    order.dispute_status = "dismissed"
    order.dispute_resolution = "dismissed"
    order.dispute_rationale = "Dismissed by admin: quality verified within acceptable transit boundaries"
    order.status = "paid"

    payment = db.query(Payment).filter(Payment.order_id == order.id).first()
    if payment:
        payment.status = "paid"
        payment.paid_date = datetime.utcnow().date()

    db.commit()

    log_audit_event(
        db, action="dispute_dismissed", actor_id=admin_user.id, actor_role="admin",
        order_id=order.id, details={"status": "dismissed"}
    )

    farm = db.query(Farm).filter(Farm.user_id == order.farmer_id).first()
    if farm:
        update_farm_reputation(db, farm.id)

    return {"message": "Dispute dismissed successfully", "order_id": order.id, "status": "dismissed"}


@router.get("/metrics")
def get_platform_metrics(
    admin_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    total_users = db.query(User).count()
    total_farms = db.query(Farm).count()
    verified_farms = db.query(Farm).filter(Farm.verified == True).count()
    total_orders = db.query(Order).count()
    completed_orders = db.query(Order).filter(Order.status.in_(["delivered", "paid", "completed"])).count()
    disputed_orders = db.query(Order).filter(Order.dispute_flag == True).count()
    
    total_volume = db.query(func.sum(Order.total_price)).filter(Order.status.in_(["delivered", "paid", "completed"])).scalar() or 0.0

    return {
        "total_users": total_users,
        "total_farms": total_farms,
        "verified_farms": verified_farms,
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "disputed_orders": disputed_orders,
        "dispute_rate_percent": round((disputed_orders / total_orders * 100.0), 2) if total_orders > 0 else 0.0,
        "gross_trade_volume_eur": round(total_volume, 2)
    }


@router.get("/audit-logs")
def get_audit_logs(
    order_id: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(100),
    admin_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if order_id:
        query = query.filter(AuditLog.order_id == order_id)
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    if action:
        query = query.filter(AuditLog.action == action)

    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()


@router.get("/settings")
def get_admin_settings(
    admin_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    all_settings = db.query(AdminSetting).all()
    setting_map = {s.setting_key: s.setting_value for s in all_settings}

    return {
        "variance_tolerance_percent": setting_map.get("variance_tolerance_percent", settings.VARIANCE_TOLERANCE_PERCENT),
        "min_listing_grade": setting_map.get("min_listing_grade", settings.MIN_LISTING_GRADE),
        "commission_percent": setting_map.get("commission_percent", settings.COMMISSION_PERCENT),
        "payment_terms_days": setting_map.get("payment_terms_days", settings.PAYMENT_TERMS_DAYS)
    }


@router.put("/settings")
def update_admin_settings(
    settings_in: AdminSettingsUpdate,
    admin_user: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    def set_key(key: str, val):
        if val is None:
            return
        row = db.query(AdminSetting).filter(AdminSetting.setting_key == key).first()
        if not row:
            row = AdminSetting(setting_key=key, setting_value=val)
            db.add(row)
        else:
            row.setting_value = val

    set_key("variance_tolerance_percent", settings_in.variance_tolerance_percent)
    set_key("min_listing_grade", settings_in.min_listing_grade)
    set_key("commission_percent", settings_in.commission_percent)
    set_key("payment_terms_days", settings_in.payment_terms_days)

    db.commit()

    log_audit_event(db, action="admin_settings_updated", actor_id=admin_user.id, actor_role="admin", details=settings_in.model_dump())
    return {"message": "Admin settings updated successfully"}
