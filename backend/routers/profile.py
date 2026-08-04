"""
User Profile Router for OrganicLink (Build Prompt V6 - Change 1).
Provides editable own profile and privacy-compliant public profile endpoints.
"""

import os
import re
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from database import get_db
from models.all_models import User, Farm, Product, RatingReview, Order, Photo
from schemas.schemas import ProfileUpdate, UserProfileResponse, PublicProfileResponse
from routers.auth import get_current_user
from services.geo import geocode_irish_location
from services.documents import UPLOADS_DIR

router = APIRouter(prefix="/api", tags=["Profiles"])

EIRCODE_REGEX = re.compile(r"^[A-Za-z0-9]{3}\s?[A-Za-z0-9]{4}$")

IRISH_COUNTIES = [
    "Carlow", "Cavan", "Clare", "Cork", "Donegal", "Dublin", "Galway",
    "Kerry", "Kildare", "Kilkenny", "Laois", "Leitrim", "Limerick",
    "Longford", "Louth", "Mayo", "Meath", "Monaghan", "Offaly",
    "Roscommon", "Sligo", "Tipperary", "Waterford", "Westmeath",
    "Wexford", "Wicklow"
]


@router.get("/profile/me", response_model=UserProfileResponse)
def get_own_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm_data = None
    if current_user.role == "farmer":
        farm = db.query(Farm).filter(Farm.user_id == current_user.id).first()
        if farm:
            farm_data = {
                "id": farm.id,
                "farm_name": farm.farm_name,
                "town": farm.town,
                "county": farm.county,
                "eircode": farm.eircode,
                "size_hectares": farm.size_hectares,
                "years_farming_organic": farm.years_farming_organic,
                "provides_own_transport": farm.provides_own_transport,
                "produce_list": farm.produce_list or [],
                "photo_urls": farm.photo_urls or [],
                "organic_cert_body": farm.organic_cert_body,
                "organic_cert_number": farm.organic_cert_number,
                "cert_issue_date": farm.cert_issue_date.isoformat() if farm.cert_issue_date else None,
                "cert_expiry_date": farm.cert_expiry_date.isoformat() if farm.cert_expiry_date else None,
                "cert_doc_url": farm.cert_doc_url,
                "verification_status": farm.verification_status,
                "reputation_score": farm.reputation_score,
                "total_orders_completed": farm.total_orders_completed,
                "average_quality_score": farm.average_quality_score,
            }

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        phone=current_user.phone,
        role=current_user.role,
        status=current_user.status or "verified",
        town=current_user.town,
        county=current_user.county,
        eircode=current_user.eircode,
        latitude=current_user.latitude,
        longitude=current_user.longitude,
        geocode_source=current_user.geocode_source,
        buyer_type=current_user.buyer_type,
        business_name=current_user.business_name,
        vat_number=current_user.vat_number,
        delivery_address=current_user.delivery_address,
        typical_order_size=current_user.typical_order_size,
        profile_photo_url=current_user.profile_photo_url,
        created_at=current_user.created_at,
        farm=farm_data
    )


@router.patch("/profile/me", response_model=UserProfileResponse)
def update_own_profile(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if profile_in.name is not None:
        current_user.name = profile_in.name
    if profile_in.phone is not None:
        current_user.phone = profile_in.phone
    if profile_in.town is not None:
        current_user.town = profile_in.town
    if profile_in.county is not None:
        if profile_in.county and profile_in.county not in IRISH_COUNTIES:
            raise HTTPException(status_code=400, detail=f"Invalid county. Must be one of 26 Irish counties.")
        current_user.county = profile_in.county
    if profile_in.eircode is not None:
        if profile_in.eircode and not EIRCODE_REGEX.match(profile_in.eircode.strip()):
            raise HTTPException(status_code=400, detail="Invalid Eircode format. Example: 'A65 F4E2'")
        current_user.eircode = profile_in.eircode

    # Geocode location if eircode/town updated
    if profile_in.eircode or profile_in.town:
        lat, lng = geocode_irish_location(eircode=current_user.eircode, town=current_user.town)
        current_user.latitude = lat
        current_user.longitude = lng
        current_user.geocode_source = "eircode_routing_key" if current_user.eircode else "town_centroid"

    # Buyer fields
    if current_user.role != "farmer":
        if profile_in.buyer_type is not None:
            current_user.buyer_type = profile_in.buyer_type
        if profile_in.business_name is not None:
            current_user.business_name = profile_in.business_name
        if profile_in.vat_number is not None:
            current_user.vat_number = profile_in.vat_number
        if profile_in.delivery_address is not None:
            current_user.delivery_address = profile_in.delivery_address
        if profile_in.typical_order_size is not None:
            current_user.typical_order_size = profile_in.typical_order_size

    # Farmer fields
    if current_user.role == "farmer":
        farm = db.query(Farm).filter(Farm.user_id == current_user.id).first()
        if not farm:
            farm = Farm(
                user_id=current_user.id,
                farm_name=profile_in.farm_name or f"{current_user.name}'s Farm",
                town=current_user.town or "Unknown",
                county=current_user.county or "Cork",
                eircode=current_user.eircode or "T12 AB34",
                latitude=current_user.latitude,
                longitude=current_user.longitude,
            )
            db.add(farm)
            db.commit()
            db.refresh(farm)

        if profile_in.farm_name is not None:
            farm.farm_name = profile_in.farm_name
        if profile_in.size_hectares is not None:
            farm.size_hectares = profile_in.size_hectares
        if profile_in.years_farming_organic is not None:
            farm.years_farming_organic = profile_in.years_farming_organic
        if profile_in.organic_cert_body is not None:
            farm.organic_cert_body = profile_in.organic_cert_body
        if profile_in.organic_cert_number is not None:
            farm.organic_cert_number = profile_in.organic_cert_number
        if profile_in.cert_expiry_date is not None:
            farm.cert_expiry_date = profile_in.cert_expiry_date
        if profile_in.produce_list is not None:
            farm.produce_list = profile_in.produce_list
        if profile_in.provides_own_transport is not None:
            farm.provides_own_transport = profile_in.provides_own_transport

        if current_user.town:
            farm.town = current_user.town
        if current_user.county:
            farm.county = current_user.county
        if current_user.eircode:
            farm.eircode = current_user.eircode

    db.commit()
    db.refresh(current_user)
    return get_own_profile(current_user=current_user, db=db)


@router.post("/profile/me/photo")
def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    filename = f"profile_{current_user.id[:8]}_{file.filename}"
    file_path = os.path.join(UPLOADS_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    photo_url = f"/static/uploads/{filename}"
    current_user.profile_photo_url = photo_url
    db.commit()

    return {"message": "Profile photo uploaded successfully", "profile_photo_url": photo_url}


@router.post("/profile/me/certificate")
def upload_farmer_certificate(
    file: UploadFile = File(...),
    cert_body: Optional[str] = Form("IOA"),
    cert_number: Optional[str] = Form("IOA-REG-2026"),
    expiry_date: Optional[str] = Form("2027-12-31"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "farmer":
        raise HTTPException(status_code=403, detail="Only farmers can upload organic certificates.")

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    filename = f"cert_{current_user.id[:8]}_{file.filename}"
    file_path = os.path.join(UPLOADS_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    doc_url = f"/static/uploads/{filename}"

    farm = db.query(Farm).filter(Farm.user_id == current_user.id).first()
    if farm:
        farm.organic_cert_body = cert_body
        farm.organic_cert_number = cert_number
        try:
            farm.cert_expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        except Exception:
            pass
        farm.cert_doc_url = doc_url
        farm.verification_status = "pending_verification"
        db.commit()

    return {
        "message": "Certificate uploaded successfully. Admin verification triggered.",
        "cert_doc_url": doc_url,
        "verification_status": "pending_verification"
    }


@router.get("/users/{user_id}/public", response_model=PublicProfileResponse)
def get_public_profile(
    user_id: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")

    farm_data = None
    active_listings = []

    if user.role == "farmer":
        farm = db.query(Farm).filter(Farm.user_id == user.id).first()
        if farm:
            farm_data = {
                "id": farm.id,
                "farm_name": farm.farm_name,
                "town": farm.town,
                "county": farm.county,
                "size_hectares": farm.size_hectares,
                "produce_list": farm.produce_list or [],
                "organic_cert_body": farm.organic_cert_body,
                "verification_status": farm.verification_status,
                "reputation_score": farm.reputation_score,
                "total_orders_completed": farm.total_orders_completed,
                "average_quality_score": farm.average_quality_score,
                "provides_own_transport": farm.provides_own_transport,
            }
            # Active listings for farmer
            prods = db.query(Product).filter(
                Product.farm_id == farm.id,
                Product.status == "listed"
            ).all()
            for p in prods:
                active_listings.append({
                    "id": p.id,
                    "product_type": p.product_type,
                    "variety": p.variety,
                    "available_quantity": p.available_quantity,
                    "quantity_unit": p.quantity_unit,
                    "price_per_unit": p.price_per_unit,
                    "quality_grade": p.quality_grade,
                    "quality_score": p.quality_score,
                    "image_url": p.image_url
                })

    # Recent reviews
    reviews_raw = db.query(RatingReview).filter(RatingReview.ratee_id == user.id).limit(5).all()
    reviews = [
        {
            "id": r.id,
            "rating": r.rating_stars,
            "review_text": r.review_text,
            "reviewer_role": r.reviewer_role,
            "created_at": r.created_at.isoformat()
        } for r in reviews_raw
    ]

    # PRIVACY RULE CARRIED FORWARD: Eircode and exact address are HIDDEN!
    return PublicProfileResponse(
        id=user.id,
        name=user.name,
        role=user.role,
        status=user.status or "verified",
        town=user.town or (farm_data["town"] if farm_data else "Ireland"),
        county=user.county or (farm_data["county"] if farm_data else "Ireland"),
        profile_photo_url=user.profile_photo_url,
        verified=user.verified,
        reputation_score=farm_data["reputation_score"] if farm_data else 90.0,
        total_completed_orders=farm_data["total_orders_completed"] if farm_data else 0,
        average_quality_score=farm_data["average_quality_score"] if farm_data else None,
        member_since=user.created_at,
        farm=farm_data,
        recent_reviews=reviews,
        active_listings=active_listings
    )
