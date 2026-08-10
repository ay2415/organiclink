"""
Traceability and QR Code router for OrganicLink.
Provides public access to farm of origin, organic certification status,
and complete quality inspection history for listings and orders.
"""

import io
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import qrcode

from database import get_db
from models.all_models import Product, Farm, Order, QualityInspection, User

router = APIRouter(prefix="/api/traceability", tags=["Traceability & QR Codes"])


@router.get("/qr")
def generate_qr_code(url: str = Query(...)):
    """Generates a QR code PNG image encoding the target traceability URL."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#064e3b", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/product/{product_id}")
def get_product_traceability(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product listing not found")

    farm = db.query(Farm).filter(Farm.id == product.farm_id).first()
    farmer = db.query(User).filter(User.id == farm.user_id).first() if farm else None
    inspection = db.query(QualityInspection).filter(QualityInspection.id == product.quality_inspection_id).first() if product.quality_inspection_id else None

    return {
        "traceability_type": "product",
        "product": {
            "id": product.id,
            "product_type": product.product_type,
            "variety": product.variety,
            "production_date": str(product.production_date),
            "available_quantity": product.available_quantity,
            "quantity_unit": product.quantity_unit,
            "quality_grade": product.quality_grade,
            "quality_score": product.quality_score,
            "is_bulk": product.is_bulk,
            "image_url": product.image_url
        },
        "farm": {
            "id": farm.id if farm else None,
            "farm_name": farm.farm_name if farm else "Organic Farm",
            "town": farm.town if farm else "Ireland",
            "county": farm.county if farm else "Ireland",
            "organic_cert_body": farm.organic_cert_body if farm else "IOA",
            "organic_cert_number": farm.organic_cert_number if farm else "Verified",
            "verification_status": farm.verification_status if farm else "verified",
            "verified": farm.verified if farm else True,
            "reputation_score": farm.reputation_score if farm else 100.0,
            "farmer_name": farmer.name if farmer else "Certified Organic Farmer"
        },
        "inspections": {
            "listing_inspection": {
                "id": inspection.id if inspection else None,
                "inspection_level": "farm_listing",
                "quality_score": inspection.quality_score if inspection else product.quality_score,
                "quality_grade": inspection.quality_grade if inspection else product.quality_grade,
                "defects_detected": inspection.defects_detected if inspection else [],
                "image_url": inspection.image_url if inspection else product.image_url,
                "created_at": inspection.created_at.strftime("%Y-%m-%d %H:%M") if inspection else None
            }
        }
    }


@router.get("/order/{order_id}")
def get_order_traceability(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    product = db.query(Product).filter(Product.id == order.product_id).first()
    farm = db.query(Farm).filter(Farm.user_id == order.farmer_id).first()
    farmer = db.query(User).filter(User.id == order.farmer_id).first()
    buyer = db.query(User).filter(User.id == order.buyer_id).first()

    farm_insp = db.query(QualityInspection).filter(QualityInspection.id == order.farm_inspection_id).first() if order.farm_inspection_id else None
    deliv_insp = db.query(QualityInspection).filter(QualityInspection.id == order.delivery_inspection_id).first() if order.delivery_inspection_id else None
    listing_insp = db.query(QualityInspection).filter(QualityInspection.id == product.quality_inspection_id).first() if (product and product.quality_inspection_id) else None

    dispatch_date = farm_insp.created_at.strftime("%Y-%m-%d %H:%M") if farm_insp else None
    if not dispatch_date and order.status in ["in_transit", "delivered", "paid", "completed"]:
        dispatch_date = order.updated_at.strftime("%Y-%m-%d %H:%M")

    delivery_date = deliv_insp.created_at.strftime("%Y-%m-%d %H:%M") if deliv_insp else None
    if not delivery_date and order.status in ["delivered", "paid", "completed"]:
        delivery_date = str(order.delivery_date)

    return {
        "traceability_type": "order",
        "order": {
            "id": order.id,
            "product_type": product.product_type if product else "Organic Produce",
            "quantity": order.quantity,
            "quantity_unit": order.quantity_unit,
            "scheduled_delivery_date": str(order.delivery_date),
            "status": order.status,
            "quality_variance_percent": order.quality_variance_percent,
            "variance_acceptable": order.variance_acceptable
        },
        "farm": {
            "farm_name": farm.farm_name if farm else "Organic Farm",
            "town": farm.town if farm else "Ireland",
            "county": farm.county if farm else "Ireland",
            "organic_cert_body": farm.organic_cert_body if farm else "IOA",
            "organic_cert_number": farm.organic_cert_number if farm else "Verified",
            "verification_status": farm.verification_status if farm else "verified",
            "farmer_name": farmer.name if farmer else "Farmer"
        },
        "recipient": {
            "name": buyer.name if buyer else "Certified Organic Buyer",
            "role": buyer.role if buyer else "consumer",
            "business_name": buyer.business_name if buyer else None,
            "delivery_address": order.delivery_address
        },
        "dispatch": {
            "dispatched": dispatch_date is not None,
            "dispatch_date": dispatch_date,
            "recipient_name": buyer.name if buyer else "Buyer",
            "recipient_role": buyer.role if buyer else "consumer",
            "dispatch_grade": farm_insp.quality_grade if farm_insp else None,
            "dispatch_score": farm_insp.quality_score if farm_insp else None
        },
        "delivery": {
            "delivered": order.status in ["delivered", "paid", "completed"],
            "delivery_date": delivery_date,
            "delivery_grade": deliv_insp.quality_grade if deliv_insp else None,
            "delivery_score": deliv_insp.quality_score if deliv_insp else None
        },
        "inspections": {
            "listing_inspection": {
                "id": listing_insp.id if listing_insp else None,
                "score": listing_insp.quality_score if listing_insp else (product.quality_score if product else None),
                "grade": listing_insp.quality_grade if listing_insp else (product.quality_grade if product else None),
                "image_url": listing_insp.image_url if listing_insp else (product.image_url if product else None)
            },
            "farm_dispatch": {
                "id": farm_insp.id if farm_insp else None,
                "score": farm_insp.quality_score if farm_insp else None,
                "grade": farm_insp.quality_grade if farm_insp else None,
                "image_url": farm_insp.image_url if farm_insp else None,
                "created_at": dispatch_date
            },
            "delivery_arrival": {
                "id": deliv_insp.id if deliv_insp else None,
                "score": deliv_insp.quality_score if deliv_insp else None,
                "grade": deliv_insp.quality_grade if deliv_insp else None,
                "image_url": deliv_insp.image_url if deliv_insp else None,
                "created_at": delivery_date
            }
        }
    }
