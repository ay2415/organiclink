"""
Farms, production history, and surplus calculation router for OrganicLink.
"""

import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import User, Farm, ProductionHistory, Contract, Product, Order, QualityInspection, RatingReview
from schemas.schemas import (
    FarmCreate, FarmUpdate, FarmResponse, ProductionCreate, ProductionResponse,
    SurplusSuggestion, ContractResponse, ProductResponse, RatingResponse
)
from routers.auth import get_current_user, require_role
from services.geo import geocode_irish_location
from services.documents import UPLOADS_DIR

router = APIRouter(prefix="/api/farms", tags=["Farms"])


@router.post("", response_model=FarmResponse)
def create_farm(
    farm_in: FarmCreate,
    current_user: User = Depends(require_role(["farmer"])),
    db: Session = Depends(get_db)
):
    existing = db.query(Farm).filter(Farm.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already owns a registered farm")

    lat, lng = geocode_irish_location(eircode=farm_in.eircode, town=farm_in.town)

    farm = Farm(
        user_id=current_user.id,
        farm_name=farm_in.farm_name,
        town=farm_in.town,
        county=farm_in.county,
        eircode=farm_in.eircode,
        latitude=lat,
        longitude=lng,
        size_hectares=farm_in.size_hectares,
        produce_list=farm_in.produce_list,
        organic_cert_body=farm_in.organic_cert_body,
        organic_cert_number=farm_in.organic_cert_number,
        cert_issue_date=farm_in.cert_issue_date,
        cert_expiry_date=farm_in.cert_expiry_date,
        farm_type=farm_in.farm_type,
        description=farm_in.description,
        verified=False
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("/{farm_id}")
def get_farm_profile(farm_id: str, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    contracts = db.query(Contract).filter(Contract.farm_id == farm_id, Contract.status == "active").all()
    active_products = db.query(Product).filter(Product.farm_id == farm_id, Product.status == "listed").all()
    reviews = db.query(RatingReview).filter(RatingReview.ratee_id == farm.user_id).all()

    return {
        "farm": farm,
        "active_contracts": contracts,
        "active_listings": active_products,
        "ratings_reviews": reviews
    }


@router.put("/{farm_id}", response_model=FarmResponse)
def update_farm(
    farm_id: str,
    farm_in: FarmUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    if farm.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to edit this farm")

    if farm_in.farm_name is not None:
        farm.farm_name = farm_in.farm_name
    if farm_in.town is not None or farm_in.eircode is not None:
        town = farm_in.town or farm.town
        eircode = farm_in.eircode or farm.eircode
        farm.town = town
        if farm_in.county:
            farm.county = farm_in.county
        if farm_in.eircode:
            farm.eircode = farm_in.eircode
        lat, lng = geocode_irish_location(eircode=eircode, town=town)
        farm.latitude = lat
        farm.longitude = lng
    if farm_in.size_hectares is not None:
        farm.size_hectares = farm_in.size_hectares
    if farm_in.produce_list is not None:
        farm.produce_list = farm_in.produce_list
    if farm_in.description is not None:
        farm.description = farm_in.description

    db.commit()
    db.refresh(farm)
    return farm


@router.post("/{farm_id}/certification")
def upload_certification(
    farm_id: str,
    file: UploadFile = File(...),
    cert_body: str = Form(...),
    cert_number: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    if farm.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    ext = os.path.splitext(file.filename)[1]
    filename = f"cert_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOADS_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(file.file.read())

    farm.organic_cert_body = cert_body
    farm.organic_cert_number = cert_number
    farm.cert_doc_url = f"/static/uploads/{filename}"
    db.commit()

    return {"message": "Certification document uploaded successfully", "cert_doc_url": farm.cert_doc_url}


# --- Production History ---
@router.get("/{farm_id}/production", response_model=List[ProductionResponse])
def get_production_history(farm_id: str, db: Session = Depends(get_db)):
    return db.query(ProductionHistory).filter(ProductionHistory.farm_id == farm_id).order_by(ProductionHistory.year.desc(), ProductionHistory.month.desc()).all()


@router.post("/{farm_id}/production", response_model=ProductionResponse)
def add_production_row(
    farm_id: str,
    prod_in: ProductionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm or (farm.user_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Not authorized")

    row = ProductionHistory(
        farm_id=farm_id,
        product_type=prod_in.product_type.lower(),
        year=prod_in.year,
        month=prod_in.month,
        quantity=prod_in.quantity,
        unit=prod_in.unit.lower()
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# --- Sales History ---
@router.get("/{farm_id}/sales-history")
def get_sales_history(farm_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    orders = db.query(Order).filter(
        Order.farmer_id == farm.user_id,
        Order.status.in_(["delivered", "paid", "completed"])
    ).order_by(Order.created_at.desc()).all()

    results = []
    for o in orders:
        product = db.query(Product).filter(Product.id == o.product_id).first()
        buyer = db.query(User).filter(User.id == o.buyer_id).first()
        farm_insp = db.query(QualityInspection).filter(QualityInspection.id == o.farm_inspection_id).first() if o.farm_inspection_id else None

        results.append({
            "order_id": o.id,
            "product_type": product.product_type if product else "Organic Produce",
            "buyer_name": buyer.name if buyer else "Buyer",
            "buyer_role": buyer.role if buyer else "buyer",
            "quantity": o.quantity,
            "quantity_unit": o.quantity_unit,
            "final_price": o.total_price,
            "date": o.created_at.strftime("%Y-%m-%d"),
            "quality_grade": farm_insp.quality_grade if farm_insp else "A",
            "quality_score": farm_insp.quality_score if farm_insp else 88.0
        })
    return results


# --- Surplus Calculation Endpoint ---
@router.get("/{farm_id}/surplus-suggestion", response_model=List[SurplusSuggestion])
def calculate_surplus_suggestion(
    farm_id: str,
    db: Session = Depends(get_db)
):
    """
    Computes surplus per product type:
    produced (this period from production_history) minus committed (from active contracts).
    E.g. Onion: 100kg produced - 80kg committed = 20kg surplus to list.
    """
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    # Aggregate production history (most recent year/month entries or defaults)
    prod_rows = db.query(ProductionHistory).filter(ProductionHistory.farm_id == farm_id).all()
    prod_map = {}
    for p in prod_rows:
        key = p.product_type.lower()
        if key not in prod_map:
            prod_map[key] = {"quantity": 0.0, "unit": p.unit}
        prod_map[key]["quantity"] += p.quantity

    # Aggregate active contracts
    contracts = db.query(Contract).filter(Contract.farm_id == farm_id, Contract.status == "active").all()
    contract_map = {}
    for c in contracts:
        key = c.product_type.lower()
        if key not in contract_map:
            contract_map[key] = 0.0
        contract_map[key] += c.committed_quantity

    suggestions = []
    # Process all unique products
    all_products = set(prod_map.keys()).union(set(contract_map.keys()))
    if not all_products:
        all_products = {"onion", "milk"} # default fallback

    for p_type in all_products:
        produced = prod_map.get(p_type, {}).get("quantity", 100.0)
        unit = prod_map.get(p_type, {}).get("unit", "kg" if p_type != "milk" else "litre")
        committed = contract_map.get(p_type, 0.0)

        surplus = max(0.0, produced - committed)

        suggestions.append({
            "product_type": p_type,
            "produced_quantity": produced,
            "committed_quantity": committed,
            "suggested_surplus": round(surplus, 1),
            "unit": unit
        })

    return suggestions
