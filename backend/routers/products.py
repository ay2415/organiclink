"""
Products and Marketplace feed router for OrganicLink.
Wired to the Computer Vision grading gate.
"""

import os
import uuid
import json
from datetime import date, datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.all_models import Product, Farm, QualityInspection, ProductionHistory, User, ProductType, Photo
from schemas.schemas import ProductResponse
from routers.auth import get_current_user, require_role
from cv.inference import get_inference_engine
from services.geo import haversine_distance, geocode_irish_location
from services.demand import get_product_demand
from services.documents import UPLOADS_DIR, generate_quality_certificate_pdf

router = APIRouter(prefix="/api", tags=["Products & Marketplace"])


@router.post("/farms/{farm_id}/products", response_model=ProductResponse)
def create_product_listing(
    farm_id: str,
    product_type: str = Form(...),
    variety: Optional[str] = Form(None),
    production_date: str = Form(...), # YYYY-MM-DD
    available_quantity: float = Form(...),
    quantity_unit: str = Form(...), # kg, litre, box
    price_per_unit: float = Form(...),
    buyer_types_open_to: str = Form("[]"), # JSON array string or comma separated
    provides_transport: bool = Form(False),
    description: Optional[str] = Form(None),
    hours_active: int = Form(24),
    image: UploadFile = File(...),
    current_user: User = Depends(require_role(["farmer", "admin"])),
    db: Session = Depends(get_db)
):
    if current_user.role != "farmer" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only users with role 'farmer' may create listings.")

    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    if farm.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to list for this farm")

    # A7. Organic Verification Gate Enforcement
    if farm.verification_status != "verified" and not farm.verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Farm organic certification is pending verification or expired. Unverified farms cannot publish listings."
        )

    # 1. Save uploaded image
    ext = os.path.splitext(image.filename)[1] or ".jpg"
    filename = f"prod_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOADS_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(image.file.read())
    
    image_url = f"/static/uploads/{filename}"

    # Check if product is CV gradable (A4)
    prod_type_ref = db.query(ProductType).filter(ProductType.id == product_type.lower()).first()
    is_cv_gradable = prod_type_ref.cv_gradable if prod_type_ref else True

    score = None
    grade = None
    cv_result = None

    if is_cv_gradable:
        # 2. Run Computer Vision Quality Grading for gradable produce
        engine = get_inference_engine()
        cv_result = engine.analyze_image(filepath, expected_product=product_type)

        if cv_result.get("product_mismatch"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=cv_result.get("message", "Product mismatch detected.")
            )

        score = cv_result.get("quality_score", 0.0)
        grade = cv_result.get("quality_grade", "N/A")
        defects = cv_result.get("cv_breakdown", {}).get("detected_defects", [])

        # 3. Listing Gate Enforcement: Grade R is REJECTED
        if grade == "R":
            defect_str = ", ".join(defects) if defects else "severely damaged produce visual indicators"
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Produce Quality Inspection REJECTED (Grade R, Score {score:.1f}/100). Defects detected: {defect_str}. Only produce of Grade A, B, or C may be listed."
            )

    # Parse buyer types
    try:
        buyer_roles = json.loads(buyer_types_open_to)
    except Exception:
        buyer_roles = [r.strip() for r in buyer_types_open_to.split(",") if r.strip()]

    # 4. Create Quality Inspection record if gradable
    prod_date_obj = datetime.strptime(production_date, "%Y-%m-%d").date()
    inspection_id = None

    if is_cv_gradable and cv_result:
        inspection = QualityInspection(
            inspection_level="farm",
            image_url=image_url,
            cv_results=cv_result.get("cv_breakdown", {}),
            quality_score=score,
            quality_grade=grade,
            defects_detected=cv_result.get("cv_breakdown", {}).get("detected_defects", []),
            model_confidence=cv_result.get("neural_confidence", 0.0),
            model_version=cv_result.get("model_version", "resnet18-multihead-v3"),
            inspector_id=current_user.id
        )
        db.add(inspection)
        db.flush()
        inspection_id = inspection.id

    # Generate PDF certificate only if CV gradable and inspection exists
    cert_url = None
    if is_cv_gradable and inspection:
        cert_url = generate_quality_certificate_pdf(
            inspection_data={
                "id": inspection.id,
                "inspection_level": "farm",
                "quality_score": score,
                "quality_grade": grade,
                "cv_results": cv_result.get("cv_breakdown", {}) if cv_result else {},
                "defects_detected": defects,
                "model_confidence": cv_result.get("neural_confidence", 0.0) if cv_result else 0.0,
                "model_version": cv_result.get("model_version", "resnet18-multihead-v3") if cv_result else "n/a",
                "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            },
            farm_name=farm.farm_name,
            product_name=product_type.title()
        )

    # 5. Demand Score Lookup
    demand_info = get_product_demand(db, product_type=product_type, county=farm.county)

    # 6. Create Product Listing
    product = Product(
        farm_id=farm_id,
        product_type=product_type.lower(),
        variety=variety,
        production_date=prod_date_obj,
        available_quantity=available_quantity,
        quantity_unit=quantity_unit.lower(),
        price_per_unit=price_per_unit,
        buyer_types_open_to=buyer_roles,
        provides_transport=provides_transport,
        image_url=image_url,
        quality_grade=grade if is_cv_gradable else None,
        quality_score=score if is_cv_gradable else None,
        quality_inspection_id=inspection.id if (is_cv_gradable and inspection) else None,
        demand_score=demand_info["demand_score"],
        demand_is_estimate=demand_info["is_estimate"],
        status="listed",
        description=description,
        expires_at=datetime.utcnow() + timedelta(hours=hours_active)
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    if is_cv_gradable and inspection:
        inspection.product_id = product.id
        db.commit()

    res = ProductResponse.model_validate(product)
    res.farm_name = farm.farm_name
    res.farmer_name = current_user.name
    res.town = farm.town
    res.county = farm.county
    res.farmer_reputation = farm.reputation_score
    res.cv_breakdown = cv_result
    return res


class ProductPriceUpdate(BaseModel):
    price_per_unit: float


@router.patch("/products/{product_id}/price", response_model=ProductResponse)
def update_product_price(
    product_id: str,
    price_in: ProductPriceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if price_in.price_per_unit <= 0:
        raise HTTPException(status_code=400, detail="Price per unit must be greater than zero")

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product listing not found")

    farm = db.query(Farm).filter(Farm.id == product.farm_id).first()
    if not farm or (farm.user_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Not authorized to edit price for this listing")

    product.price_per_unit = round(price_in.price_per_unit, 2)
    db.commit()
    db.refresh(product)

    res = ProductResponse.model_validate(product)
    res.farm_name = farm.farm_name
    res.farmer_name = current_user.name
    res.town = farm.town
    res.county = farm.county
    res.farmer_reputation = farm.reputation_score
    return res


@router.get("/marketplace")
def get_marketplace_feed(
    product_type: Optional[str] = Query(None),
    county: Optional[str] = Query(None),
    user_lat: Optional[float] = Query(None),
    user_lng: Optional[float] = Query(None),
    max_distance_km: Optional[float] = Query(None),
    min_grade: Optional[str] = Query(None), # A, B, C
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    buyer_type: Optional[str] = Query(None),
    sort: Optional[str] = Query("newest"), # distance, price, grade, newest
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(
        Product.status == "listed",
        (Product.expires_at == None) | (Product.expires_at > datetime.utcnow())
    )

    if product_type:
        query = query.filter(Product.product_type == product_type.lower())

    if min_price is not None:
        query = query.filter(Product.price_per_unit >= min_price)
    if max_price is not None:
        query = query.filter(Product.price_per_unit <= max_price)

    grade_map = {"A": 3, "B": 2, "C": 1}
    if min_grade and min_grade in grade_map:
        min_val = grade_map[min_grade]
        allowed_grades = [g for g, v in grade_map.items() if v >= min_val]
        query = query.filter(Product.quality_grade.in_(allowed_grades))

    products = query.all()

    # User coordinates fallback if not passed
    ref_lat = user_lat if user_lat is not None else 53.3498 # Dublin default
    ref_lng = user_lng if user_lng is not None else -6.2603

    results = []
    for p in products:
        farm = db.query(Farm).filter(Farm.id == p.farm_id).first()
        if not farm:
            continue

        if county and farm.county.lower() != county.lower():
            continue

        dist_km = haversine_distance(ref_lat, ref_lng, farm.latitude or 53.3498, farm.longitude or -6.2603)

        if max_distance_km is not None and dist_km > max_distance_km:
            continue

        if buyer_type and p.buyer_types_open_to and buyer_type not in p.buyer_types_open_to:
            pass # Keep available for general market

        owner = db.query(User).filter(User.id == farm.user_id).first()

        card = {
            "id": p.id,
            "farm_id": farm.id,
            "farm_name": farm.farm_name,
            "farmer_name": owner.name if owner else "Farmer",
            "town": farm.town,
            "county": farm.county,
            "distance_km": dist_km,
            "farmer_reputation": farm.reputation_score,
            "product_type": p.product_type,
            "variety": p.variety,
            "production_date": str(p.production_date),
            "available_quantity": p.available_quantity,
            "quantity_unit": p.quantity_unit,
            "price_per_unit": p.price_per_unit,
            "buyer_types_open_to": p.buyer_types_open_to or [],
            "provides_transport": p.provides_transport,
            "image_url": p.image_url,
            "quality_grade": p.quality_grade,
            "quality_score": p.quality_score,
            "demand_score": p.demand_score,
            "demand_is_estimate": p.demand_is_estimate,
            "status": p.status,
            "description": p.description,
            "created_at": p.created_at
        }
        results.append(card)

    # Sorting
    if sort == "distance":
        results.sort(key=lambda x: x["distance_km"])
    elif sort == "price":
        results.sort(key=lambda x: x["price_per_unit"])
    elif sort == "grade":
        results.sort(key=lambda x: grade_map.get(x["quality_grade"], 0), reverse=True)
    else: # newest
        results.sort(key=lambda x: x["created_at"], reverse=True)

    return results


@router.get("/products/{product_id}")
def get_product_detail(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product listing not found")

    farm = db.query(Farm).filter(Farm.id == product.farm_id).first()
    farmer = db.query(User).filter(User.id == farm.user_id).first() if farm else None
    inspection = db.query(QualityInspection).filter(QualityInspection.id == product.quality_inspection_id).first() if product.quality_inspection_id else None

    # Certificate link
    cert_url = f"/static/pdf/cert_{inspection.id[:8]}.pdf" if inspection else None

    demand_info = get_product_demand(db, product_type=product.product_type, county=farm.county if farm else None)

    return {
        "product": product,
        "farm": farm,
        "farmer": {
            "name": farmer.name if farmer else "Farmer",
            "phone": farmer.phone if farmer else None,
            "reputation_score": farm.reputation_score if farm else 85.0
        },
        "inspection": inspection,
        "certificate_url": cert_url,
        "demand": demand_info
    }


@router.delete("/products/{product_id}")
def archive_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    farm = db.query(Farm).filter(Farm.id == product.farm_id).first()
    if farm.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    product.status = "archived"
    db.commit()
    return {"message": "Product listing archived"}


from pydantic import BaseModel
class PriceUpdate(BaseModel):
    price_per_unit: float

@router.patch("/products/{product_id}/price")
def update_product_price(
    product_id: str,
    price_update: PriceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    farm = db.query(Farm).filter(Farm.id == product.farm_id).first()
    if farm.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    product.price_per_unit = price_update.price_per_unit
    db.commit()
    
    # Return updated product
    res = ProductResponse.model_validate(product)
    res.farm_name = farm.farm_name
    return res
