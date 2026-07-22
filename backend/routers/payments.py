"""
Payments & Invoices router for OrganicLink.
"""

from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User, Payment, Order, Farm
from schemas.schemas import PaymentResponse, PaymentMarkPaid
from routers.auth import get_current_user
from services.audit import log_audit_event
from services.documents import PDF_DIR, generate_invoice_pdf
from services.reputation import update_farm_reputation

router = APIRouter(prefix="/api/payments", tags=["Payments"])


@router.get("", response_model=List[PaymentResponse])
def get_my_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "farmer":
        return db.query(Payment).filter(Payment.farmer_id == current_user.id).order_by(Payment.created_at.desc()).all()
    elif current_user.role == "admin":
        return db.query(Payment).order_by(Payment.created_at.desc()).all()
    else:
        return db.query(Payment).filter(Payment.buyer_id == current_user.id).order_by(Payment.created_at.desc()).all()


@router.put("/{payment_id}/mark-paid", response_model=PaymentResponse)
def mark_payment_paid(
    payment_id: str,
    body: PaymentMarkPaid,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    if current_user.id not in [payment.buyer_id, payment.farmer_id] and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    payment.status = "paid"
    payment.paid_date = datetime.utcnow().date()
    payment.reference_number = body.reference_number
    payment.payment_method = body.payment_method

    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if order:
        order.status = "paid"

    db.commit()

    log_audit_event(db, action="payment_settled", actor_id=current_user.id, actor_role=current_user.role, order_id=payment.order_id, details={"ref": body.reference_number, "amount": payment.amount})
    return payment


@router.get("/{payment_id}/invoice")
def download_invoice(payment_id: str, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    order = db.query(Order).filter(Order.id == payment.order_id).first()
    filename = f"invoice_{order.id[:8]}.pdf" if order else f"invoice_{payment.id[:8]}.pdf"
    filepath = f"{PDF_DIR}/{filename}"

    if not os.path.exists(filepath) and order:
        farm = db.query(Farm).filter(Farm.user_id == order.farmer_id).first()
        buyer = db.query(User).filter(User.id == order.buyer_id).first()
        generate_invoice_pdf(
            order_data={
                "id": order.id, "status": order.status, "product_type": order.product.product_type if order.product else "Produce",
                "quantity": order.quantity, "quantity_unit": order.quantity_unit, "price_per_unit": order.price_per_unit,
                "total_price": order.total_price, "delivery_address": order.delivery_address,
                "farm_grade": "A", "delivery_grade": "A", "quality_variance_percent": order.quality_variance_percent,
                "variance_acceptable": order.variance_acceptable
            },
            farmer_data={"farm_name": farm.farm_name if farm else "Farm", "town": farm.town if farm else "Town", "county": farm.county if farm else "County", "organic_cert_number": farm.organic_cert_number if farm else "IOA-0001"},
            buyer_data={"name": buyer.name if buyer else "Buyer", "role": buyer.role if buyer else "buyer"}
        )

    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="application/pdf", filename=filename)

    raise HTTPException(status_code=404, detail="Invoice PDF not generated yet")
