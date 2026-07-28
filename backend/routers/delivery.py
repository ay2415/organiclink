"""
Delivery Router for OrganicLink (Build Prompt V6 - Changes 3, 4, 5).
Handles Delivery Rules, Farmer Delivery/Pickup Slots, Order Size Tiers, and Pooled Runs.
"""

from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models.all_models import User, Farm, DeliveryRule, DeliverySlot, DeliveryRun, Order
from routers.auth import get_current_user
from services.geo import haversine_distance, geocode_irish_location

router = APIRouter(prefix="/api/delivery", tags=["Delivery Rules, Slots & Runs"])


# --- Schemas ---
class DeliveryRuleUpdate(BaseModel):
    delivers: Optional[bool] = True
    max_radius_km: Optional[int] = 30
    min_order_value_eur: Optional[float] = 0.0
    min_order_qty: Optional[float] = 0.0
    delivery_fee_eur: Optional[float] = 0.0
    free_over_eur: Optional[float] = None
    offers_pickup: Optional[bool] = True


class DeliverySlotCreate(BaseModel):
    slot_date: date
    start_time: str # e.g. "09:00"
    end_time: str   # e.g. "13:00"
    slot_type: str = "delivery" # delivery, pickup
    pickup_location: Optional[str] = None
    pickup_lat: Optional[float] = None
    pickup_lng: Optional[float] = None
    capacity_kg: Optional[float] = 100.0
    zone_note: Optional[str] = None


class DeliveryRunCreate(BaseModel):
    slot_id: Optional[str] = None
    zone_name: str # e.g. "Limerick City Run"
    zone_routing_key: str # e.g. "V94"
    target_kg: float = 50.0
    closes_at: datetime


# --- 1. Delivery Rules ---
@router.get("/rules/{farmer_id}")
def get_farmer_delivery_rules(farmer_id: str, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.user_id == farmer_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    rule = db.query(DeliveryRule).filter(DeliveryRule.farmer_id == farm.id).first()
    if not rule:
        rule = DeliveryRule(farmer_id=farm.id, max_radius_km=30, delivers=True, offers_pickup=True)
        db.add(rule)
        db.commit()
        db.refresh(rule)

    return {
        "id": rule.id,
        "farmer_id": rule.farmer_id,
        "delivers": rule.delivers,
        "max_radius_km": rule.max_radius_km,
        "min_order_value_eur": rule.min_order_value_eur,
        "min_order_qty": rule.min_order_qty,
        "delivery_fee_eur": rule.delivery_fee_eur,
        "free_over_eur": rule.free_over_eur,
        "offers_pickup": rule.offers_pickup,
    }


@router.put("/rules")
def update_delivery_rules(
    rule_in: DeliveryRuleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can update delivery rules.")

    farm = db.query(Farm).filter(Farm.user_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm profile not found")

    rule = db.query(DeliveryRule).filter(DeliveryRule.farmer_id == farm.id).first()
    if not rule:
        rule = DeliveryRule(farmer_id=farm.id)
        db.add(rule)

    if rule_in.delivers is not None: rule.delivers = rule_in.delivers
    if rule_in.max_radius_km is not None:
        if rule_in.max_radius_km > 150:
            rule.max_radius_km = 150 # capped at 150km per spec
        else:
            rule.max_radius_km = rule_in.max_radius_km
    if rule_in.min_order_value_eur is not None: rule.min_order_value_eur = rule_in.min_order_value_eur
    if rule_in.min_order_qty is not None: rule.min_order_qty = rule_in.min_order_qty
    if rule_in.delivery_fee_eur is not None: rule.delivery_fee_eur = rule_in.delivery_fee_eur
    if rule_in.free_over_eur is not None: rule.free_over_eur = rule_in.free_over_eur
    if rule_in.offers_pickup is not None: rule.offers_pickup = rule_in.offers_pickup

    db.commit()
    db.refresh(rule)
    return get_farmer_delivery_rules(farmer_id=current_user.id, db=db)


# --- 2. Delivery Slots ---
@router.get("/slots")
def get_delivery_slots(
    farmer_id: Optional[str] = Query(None),
    slot_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(DeliverySlot)
    if farmer_id:
        farm = db.query(Farm).filter(Farm.user_id == farmer_id).first()
        if farm:
            query = query.filter(DeliverySlot.farmer_id == farm.id)
    if slot_type:
        query = query.filter(DeliverySlot.slot_type == slot_type)

    # Show upcoming slots from today onwards
    query = query.filter(DeliverySlot.slot_date >= date.today())
    slots = query.order_by(DeliverySlot.slot_date.asc(), DeliverySlot.start_time.asc()).all()

    return [
        {
            "id": s.id,
            "farmer_id": s.farmer_id,
            "slot_date": s.slot_date.isoformat(),
            "start_time": s.start_time,
            "end_time": s.end_time,
            "slot_type": s.slot_type,
            "pickup_location": s.pickup_location,
            "capacity_kg": s.capacity_kg,
            "booked_kg": s.booked_kg,
            "available_kg": max(0.0, s.capacity_kg - s.booked_kg),
            "zone_note": s.zone_note,
        } for s in slots
    ]


@router.post("/slots")
def create_delivery_slot(
    slot_in: DeliverySlotCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can create delivery slots.")

    farm = db.query(Farm).filter(Farm.user_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm profile not found")

    slot = DeliverySlot(
        farmer_id=farm.id,
        slot_date=slot_in.slot_date,
        start_time=slot_in.start_time,
        end_time=slot_in.end_time,
        slot_type=slot_in.slot_type,
        pickup_location=slot_in.pickup_location,
        pickup_lat=slot_in.pickup_lat,
        pickup_lng=slot_in.pickup_lng,
        capacity_kg=slot_in.capacity_kg or 100.0,
        booked_kg=0.0,
        zone_note=slot_in.zone_note
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)

    return {
        "id": slot.id,
        "message": "Delivery/Pickup slot created successfully",
        "slot_date": slot.slot_date.isoformat(),
        "slot_type": slot.slot_type,
        "start_time": slot.start_time,
        "end_time": slot.end_time,
    }


# --- 3. Pooled Delivery Runs ---
@router.get("/runs")
def list_delivery_runs(
    routing_key: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(DeliveryRun).filter(DeliveryRun.status.in_(["open", "confirmed"]))
    if routing_key:
        query = query.filter(DeliveryRun.zone_routing_key == routing_key.strip().upper())

    runs = query.order_by(DeliveryRun.closes_at.asc()).all()
    results = []
    for r in runs:
        farmer_user = db.query(User).filter(User.id == r.farmer_id).first()
        results.append({
            "id": r.id,
            "farmer_id": r.farmer_id,
            "farmer_name": farmer_user.name if farmer_user else "Organic Farmer",
            "slot_id": r.slot_id,
            "zone_name": r.zone_name,
            "zone_routing_key": r.zone_routing_key,
            "target_kg": r.target_kg,
            "committed_kg": r.committed_kg,
            "percent_booked": round(min(100.0, (r.committed_kg / r.target_kg) * 100.0), 1) if r.target_kg > 0 else 0,
            "status": r.status,
            "closes_at": r.closes_at.isoformat(),
        })
    return results


@router.post("/runs")
def create_delivery_run(
    run_in: DeliveryRunCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can create pooled delivery runs.")

    run = DeliveryRun(
        farmer_id=current_user.id,
        slot_id=run_in.slot_id,
        zone_name=run_in.zone_name,
        zone_routing_key=run_in.zone_routing_key.strip().upper()[:3],
        target_kg=run_in.target_kg,
        committed_kg=0.0,
        status="open",
        closes_at=run_in.closes_at
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return {
        "id": run.id,
        "message": f"Pooled delivery run '{run.zone_name}' ({run.zone_routing_key}) created!",
        "target_kg": run.target_kg,
        "closes_at": run.closes_at.isoformat()
    }
