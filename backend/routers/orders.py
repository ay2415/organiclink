"""
Orders, State Machine, Negotiation, and Variance Audit router for OrganicLink.
Enforces state machine rules, quality gate before dispatch, and the +-10% variance rule.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.all_models import User, Farm, Product, Order, QualityInspection, Payment, Notification, AdminSetting, ProductType, Photo
from schemas.schemas import (
    OrderCreate, OrderNegotiate, OrderReject, OrderResponse, QualityInspectionResponse
)
from routers.auth import get_current_user
from cv.inference import get_inference_engine
from cv.grading import compute_variance
from services.audit import log_audit_event
from services.documents import UPLOADS_DIR, generate_invoice_pdf
from services.reputation import update_farm_reputation
from config import settings

router = APIRouter(prefix="/api/orders", tags=["Orders & State Machine"])


def get_variance_tolerance(db: Session) -> float:
    setting = db.query(AdminSetting).filter(AdminSetting.setting_key == "variance_tolerance_percent").first()
    if setting and setting.setting_value is not None:
        try:
            return float(setting.setting_value)
        except Exception:
            pass
    return settings.VARIANCE_TOLERANCE_PERCENT


@router.post("", response_model=OrderResponse)
def place_order(
    order_in: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == order_in.product_id).first()
    if not product or product.status != "listed":
        raise HTTPException(status_code=400, detail="Product is not available for purchase")

    if order_in.quantity > product.available_quantity:
        raise HTTPException(status_code=400, detail=f"Requested quantity ({order_in.quantity}) exceeds available stock ({product.available_quantity})")

    farm = db.query(Farm).filter(Farm.id == product.farm_id).first()
    if farm.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Farmers cannot purchase their own produce")

    total = round(order_in.quantity * product.price_per_unit, 2)

    order = Order(
        product_id=product.id,
        farmer_id=farm.user_id,
        buyer_id=current_user.id,
        quantity=order_in.quantity,
        quantity_unit=product.quantity_unit,
        price_per_unit=product.price_per_unit,
        total_price=total,
        delivery_date=order_in.delivery_date,
        delivery_address=order_in.delivery_address,
        transport_by=order_in.transport_by,
        special_requests=order_in.special_requests,
        status="pending",
        farm_inspection_id=product.quality_inspection_id # default to initial listing inspection
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # Audit log
    log_audit_event(
        db, action="order_created", actor_id=current_user.id, actor_role=current_user.role,
        order_id=order.id, details={"quantity": order_in.quantity, "total_price": total}
    )

    # Notify farmer
    notify_user(db, user_id=farm.user_id, n_type="order_received",
                msg=f"New order #{order.id[:8]} for {order_in.quantity}{product.quantity_unit} of {product.product_type}",
                url=f"/orders/{order.id}")

    return build_order_response(order, db)


@router.get("", response_model=List[OrderResponse])
def list_my_orders(
    status_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    if current_user.role == "farmer":
        # Farmer can be both seller and buyer (A1)
        role_type = Query(None)
        query = query.filter((Order.farmer_id == current_user.id) | (Order.buyer_id == current_user.id))
    elif current_user.role == "admin":
        pass # sees all
    else: # buyer roles
        query = query.filter(Order.buyer_id == current_user.id)

    if status_filter:
        query = query.filter(Order.status == status_filter)

    orders = query.order_by(Order.updated_at.desc()).all()
    return [build_order_response(o, db) for o in orders]


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_detail(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role != "admin" and current_user.id not in [order.farmer_id, order.buyer_id]:
        raise HTTPException(status_code=403, detail="Not authorized to view this order")

    return build_order_response(order, db)


# --- Order State Transitions & Negotiation ---
@router.put("/{order_id}/accept", response_model=OrderResponse)
def accept_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.id != order.farmer_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only farmer can accept order")

    if order.status not in ["pending", "negotiating"]:
        raise HTTPException(status_code=409, detail=f"Cannot accept order in status '{order.status}'")

    order.status = "accepted"
    db.commit()

    log_audit_event(db, action="order_accepted", actor_id=current_user.id, actor_role=current_user.role, order_id=order.id)
    notify_user(db, user_id=order.buyer_id, n_type="order_accepted", msg=f"Your order #{order.id[:8]} was accepted!", url=f"/orders/{order.id}")

    return build_order_response(order, db)


@router.put("/{order_id}/reject", response_model=OrderResponse)
def reject_order(
    order_id: str,
    body: OrderReject,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.id not in [order.farmer_id, order.buyer_id] and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    if order.status not in ["pending", "negotiating", "accepted"]:
        raise HTTPException(status_code=409, detail=f"Cannot reject order in status '{order.status}'")

    order.status = "rejected"
    history = list(order.negotiation_history or [])
    history.append({
        "action": "rejected",
        "actor": current_user.name,
        "role": current_user.role,
        "reason": body.reason,
        "timestamp": datetime.utcnow().isoformat()
    })
    order.negotiation_history = history
    db.commit()

    log_audit_event(db, action="order_rejected", actor_id=current_user.id, actor_role=current_user.role, order_id=order.id, details={"reason": body.reason})
    recipient = order.buyer_id if current_user.id == order.farmer_id else order.farmer_id
    notify_user(db, user_id=recipient, n_type="order_rejected", msg=f"Order #{order.id[:8]} was rejected. Reason: {body.reason}", url=f"/orders/{order.id}")

    return build_order_response(order, db)


@router.put("/{order_id}/negotiate", response_model=OrderResponse)
def negotiate_order(
    order_id: str,
    neg_in: OrderNegotiate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if current_user.id not in [order.farmer_id, order.buyer_id] and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    if order.status not in ["pending", "negotiating"]:
        raise HTTPException(status_code=409, detail=f"Cannot negotiate order in status '{order.status}'")

    order.status = "negotiating"

    if neg_in.quantity is not None:
        order.quantity = neg_in.quantity
    if neg_in.price_per_unit is not None:
        order.price_per_unit = neg_in.price_per_unit
    if neg_in.delivery_date is not None:
        order.delivery_date = neg_in.delivery_date

    order.total_price = round(order.quantity * order.price_per_unit, 2)

    history = list(order.negotiation_history or [])
    history.append({
        "action": "counter_offer",
        "actor": current_user.name,
        "role": current_user.role,
        "quantity": neg_in.quantity,
        "price_per_unit": neg_in.price_per_unit,
        "total_price": order.total_price,
        "message": neg_in.message,
        "timestamp": datetime.utcnow().isoformat()
    })
    order.negotiation_history = history
    db.commit()

    log_audit_event(db, action="order_negotiating", actor_id=current_user.id, actor_role=current_user.role, order_id=order.id, details={"new_total": order.total_price})
    other_party = order.buyer_id if current_user.id == order.farmer_id else order.farmer_id
    notify_user(db, user_id=other_party, n_type="negotiation_update", msg=f"Counter offer received for Order #{order.id[:8]}", url=f"/orders/{order.id}")

    return build_order_response(order, db)


# --- Dispatch Quality Gate ---
@router.post("/{order_id}/farm-photo")
def upload_farm_inspection_photo(
    order_id: str,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or (current_user.id != order.farmer_id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Only farmer can upload farm inspection photo")

    ext = os.path.splitext(image.filename)[1] or ".jpg"
    filename = f"farm_insp_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOADS_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(image.file.read())

    # Record photo (A5)
    photo_rec = Photo(
        file_path=image_url,
        uploaded_by=current_user.id,
        purpose="farm_inspection",
        product_id=order.product_id,
        order_id=order.id
    )
    db.add(photo_rec)

    product = db.query(Product).filter(Product.id == order.product_id).first()
    prod_type_ref = db.query(ProductType).filter(ProductType.id == product.product_type.lower()).first() if product else None
    is_cv_gradable = prod_type_ref.cv_gradable if prod_type_ref else True

    if is_cv_gradable:
        engine = get_inference_engine()
        res = engine.analyze_image(filepath)

        insp = QualityInspection(
            product_id=order.product_id,
            order_id=order.id,
            inspection_level="farm",
            image_url=image_url,
            cv_results=res.get("cv_breakdown", {}),
            quality_score=res.get("quality_score", 0.0),
            quality_grade=res.get("quality_grade", "A"),
            defects_detected=res.get("cv_breakdown", {}).get("detected_defects", []),
            model_confidence=res.get("neural_confidence", 0.0),
            model_version="imagenet-resnet18-real-v1",
            inspector_id=current_user.id
        )
        db.add(insp)
        db.commit()
        db.refresh(insp)

        order.farm_inspection_id = insp.id
        order.status = "quality_verified"
        db.commit()
        return {"message": "Farm dispatch quality inspection completed", "inspection_id": insp.id, "quality_score": insp.quality_score, "grade": insp.quality_grade}
    else:
        # Non-CV gradable item (e.g. Milk) - Skip CV scoring (A4)
        order.status = "accepted"
        db.commit()
        return {"message": "Farm dispatch photo recorded (Visual grading not applicable)", "inspection_id": None}


@router.put("/{order_id}/dispatch", response_model=OrderResponse)
def dispatch_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or (current_user.id != order.farmer_id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Only farmer can dispatch order")

    # MANDATORY QUALITY GATE: Order CANNOT reach in_transit without farm_inspection_id if CV gradable
    product = db.query(Product).filter(Product.id == order.product_id).first()
    prod_type_ref = db.query(ProductType).filter(ProductType.id == product.product_type.lower()).first() if product else None
    is_cv_gradable = prod_type_ref.cv_gradable if prod_type_ref else True

    if is_cv_gradable and not order.farm_inspection_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quality Gate Failed: Cannot dispatch order without an attached farm photo inspection. Please submit farm inspection photo first."
        )

    if order.status not in ["accepted", "quality_verified"]:
        raise HTTPException(status_code=409, detail=f"Cannot dispatch order from status '{order.status}'")

    order.status = "in_transit"
    db.commit()

    log_audit_event(db, action="order_dispatched", actor_id=current_user.id, actor_role=current_user.role, order_id=order.id)
    notify_user(db, user_id=order.buyer_id, n_type="order_in_transit", msg=f"Order #{order.id[:8]} is in transit!", url=f"/orders/{order.id}")

    return build_order_response(order, db)


# --- Delivery Inspection Photo & Variance Rule Enforcement ---
@router.post("/{order_id}/delivery-photo")
def upload_delivery_inspection_photo(
    order_id: str,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # All permissions granted: allow any authenticated user to complete delivery quality verification

    # 1. Save delivery image
    ext = os.path.splitext(image.filename)[1] or ".jpg"
    filename = f"deliv_insp_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOADS_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(image.file.read())

    image_url = f"/static/uploads/{filename}"

    # Record photo (A5)
    photo_rec = Photo(
        file_path=image_url,
        uploaded_by=current_user.id,
        purpose="delivery_inspection",
        product_id=order.product_id,
        order_id=order.id
    )
    db.add(photo_rec)

    product = db.query(Product).filter(Product.id == order.product_id).first()
    prod_type_ref = db.query(ProductType).filter(ProductType.id == product.product_type.lower()).first() if product else None
    is_cv_gradable = prod_type_ref.cv_gradable if prod_type_ref else True

    if not is_cv_gradable:
        # A4. Non-CV gradable item (Milk) - Skip CV variance check entirely
        order.status = "delivered"
        order.dispute_flag = False
        
        # Create payment record in pending status
        payment = db.query(Payment).filter(Payment.order_id == order.id).first()
        if not payment:
            payment = Payment(
                order_id=order.id,
                farmer_id=order.farmer_id,
                buyer_id=order.buyer_id,
                amount=order.total_price,
                currency="EUR",
                payment_method="bank_transfer",
                due_date=order.delivery_date,
                status="pending",
                reference_number=f"INV-{order.id[:8].upper()}"
            )
            db.add(payment)
            db.flush()

        pdf_url = generate_invoice_pdf(order, farm_score=100, deliv_score=100, variance=0)
        payment.invoice_url = pdf_url
        db.commit()

        log_audit_event(db, action="delivery_confirmed_no_cv", actor_id=current_user.id, actor_role=current_user.role, order_id=order.id)
        notify_user(db, user_id=order.farmer_id, n_type="order_delivered", msg=f"Order #{order.id[:8]} delivered! Bank transfer payment pending.", url=f"/orders/{order.id}")

        return {"message": "Milk delivery confirmed without CV variance check", "status": "delivered"}

    # 2. Run CV Analysis on delivery image for gradable produce
    engine = get_inference_engine()
    product_type_str = product.product_type if product else "unknown"
    res = engine.analyze_image(filepath, expected_product=product_type_str)

    deliv_score = res.get("quality_score") if res.get("quality_score") is not None else 85.0
    deliv_grade = res.get("quality_grade") if res.get("quality_grade") is not None else "A"

    deliv_insp = QualityInspection(
        product_id=order.product_id,
        order_id=order.id,
        inspection_level="delivery",
        image_url=image_url,
        cv_results=res.get("cv_breakdown", {}),
        quality_score=deliv_score,
        quality_grade=deliv_grade,
        defects_detected=res.get("cv_breakdown", {}).get("detected_defects", []),
        model_confidence=res.get("neural_confidence", 0.0),
        model_version=res.get("model_version", "resnet18-multihead-v3"),
        inspector_id=current_user.id
    )
    db.add(deliv_insp)
    db.commit()
    db.refresh(deliv_insp)

    order.delivery_inspection_id = deliv_insp.id

    # 3. Retrieve Farm inspection score
    farm_score = 85.0
    farm_grade = "A"
    if order.farm_inspection_id:
        farm_insp = db.query(QualityInspection).filter(QualityInspection.id == order.farm_inspection_id).first()
        if farm_insp and farm_insp.quality_score is not None:
            farm_score = farm_insp.quality_score
            farm_grade = farm_insp.quality_grade

    # 4. Variance Tolerance Logic (A6)
    tolerance = get_variance_tolerance(db)
    variance_percent = round(((farm_score - deliv_score) / farm_score) * 100.0, 2)
    grade_dropped = (farm_grade != deliv_grade)

    # Exact boundary: 10.00% passes, 10.01% disputes
    variance_acceptable = (variance_percent <= tolerance)

    order.quality_variance_percent = variance_percent
    order.variance_acceptable = variance_acceptable

    # 5. Handle Pass vs Dispute
    if variance_acceptable:
        order.status = "delivered"
        order.dispute_flag = False
        
        payment = db.query(Payment).filter(Payment.order_id == order.id).first()
        if not payment:
            payment = Payment(
                order_id=order.id,
                farmer_id=order.farmer_id,
                buyer_id=order.buyer_id,
                amount=order.total_price,
                currency="EUR",
                payment_method="bank_transfer",
                due_date=order.delivery_date,
                status="pending",
                reference_number=f"INV-{order.id[:8].upper()}"
            )
            db.add(payment)
            db.flush()

        pdf_url = generate_invoice_pdf(order, farm_score=farm_score, deliv_score=deliv_score, variance=variance_percent)
        payment.invoice_url = pdf_url
        db.commit()

        update_farm_reputation(db, order.farmer_id, deliv_score)
        log_audit_event(db, action="delivery_verified_pass", actor_id=current_user.id, actor_role=current_user.role, order_id=order.id, details={"variance_percent": variance_percent, "tolerance": tolerance, "grade_dropped": grade_dropped})
        notify_user(db, user_id=order.farmer_id, n_type="order_delivered", msg=f"Order #{order.id[:8]} quality verified! Bank transfer payment pending.", url=f"/orders/{order.id}")

        return {"message": "Delivery quality inspection passed within tolerance", "status": "delivered", "variance_percent": variance_percent, "grade_dropped": grade_dropped}
    else:
        # DISPUTE TRIGGERED: variance > 10.00%
        order.status = "disputed"
        order.dispute_flag = True
        order.dispute_reason = f"Quality score drop of {variance_percent:.2f}% exceeds tolerance threshold of {tolerance:.1f}%"
        order.dispute_status = "open"
        db.commit()

        log_audit_event(db, action="delivery_dispute_triggered", actor_id=current_user.id, actor_role=current_user.role, order_id=order.id, details={"variance_percent": variance_percent, "tolerance": tolerance, "grade_dropped": grade_dropped})
        notify_user(db, user_id=order.farmer_id, n_type="order_disputed", msg=f"ALERT: Order #{order.id[:8]} disputed due to quality drop of {variance_percent:.1f}%", url=f"/orders/{order.id}")

        return {"message": f"DISPUTE TRIGGERED: Quality score drop of {variance_percent:.2f}% exceeds tolerance of {tolerance:.1f}%", "status": "disputed", "variance_percent": variance_percent, "grade_dropped": grade_dropped}


# --- Two-Step Bank Payment Confirmation (A9) ---
@router.post("/{order_id}/payment/send")
def mark_payment_sent(
    order_id: str,
    payment_reference: Optional[str] = Form("BANK-TRANSFER"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or (current_user.id != order.buyer_id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Only buyer can mark payment as sent")

    order.buyer_payment_status = "sent"
    order.payment_reference = payment_reference

    payment = db.query(Payment).filter(Payment.order_id == order.id).first()
    if payment:
        payment.status = "sent"
        payment.reference_number = payment_reference

    db.commit()
    log_audit_event(db, action="payment_sent_by_buyer", actor_id=current_user.id, actor_role=current_user.role, order_id=order.id)
    notify_user(db, user_id=order.farmer_id, n_type="payment_sent", msg=f"Buyer marked payment sent for Order #{order.id[:8]} (Ref: {payment_reference}). Please confirm receipt.", url=f"/orders/{order.id}")
    return {"message": "Payment marked as sent by buyer", "order_id": order.id, "payment_status": "sent"}


@router.post("/{order_id}/payment/receive")
def mark_payment_received(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or (current_user.id != order.farmer_id and current_user.role != "admin"):
        raise HTTPException(status_code=403, detail="Only farmer can confirm payment receipt")

    order.farmer_payment_status = "received"
    order.status = "paid"

    payment = db.query(Payment).filter(Payment.order_id == order.id).first()
    if payment:
        payment.status = "paid"
        payment.paid_date = datetime.utcnow().date()

    db.commit()
    log_audit_event(db, action="payment_received_by_farmer", actor_id=current_user.id, actor_role=current_user.role, order_id=order.id)
    notify_user(db, user_id=order.buyer_id, n_type="payment_received", msg=f"Farmer confirmed bank transfer receipt for Order #{order.id[:8]}! Order complete.", url=f"/orders/{order.id}")
    return {"message": "Payment confirmed as received by farmer. Order complete!", "order_id": order.id, "status": "paid"}


def notify_user(db: Session, user_id: str, n_type: str, msg: str, url: str):
    noti = Notification(user_id=user_id, notification_type=n_type, message=msg, action_url=url)
    db.add(noti)
    db.commit()


def build_order_response(order: Order, db: Session) -> OrderResponse:
    farmer = db.query(User).filter(User.id == order.farmer_id).first()
    buyer = db.query(User).filter(User.id == order.buyer_id).first()
    product = db.query(Product).filter(Product.id == order.product_id).first()
    farm = db.query(Farm).filter(Farm.user_id == order.farmer_id).first()
    payment = db.query(Payment).filter(Payment.order_id == order.id).first()

    farm_insp = db.query(QualityInspection).filter(QualityInspection.id == order.farm_inspection_id).first() if order.farm_inspection_id else None
    deliv_insp = db.query(QualityInspection).filter(QualityInspection.id == order.delivery_inspection_id).first() if order.delivery_inspection_id else None

    res = OrderResponse.model_validate(order)
    res.product_type = product.product_type.title() if product else "Produce"
    res.farmer_name = farmer.name if farmer else "Farmer"
    res.buyer_name = buyer.name if buyer else "Buyer"
    res.farm_name = farm.farm_name if farm else "Organic Farm"
    res.invoice_url = payment.invoice_url if payment else None

    if farm_insp:
        res.farm_inspection = QualityInspectionResponse.model_validate(farm_insp)
    if deliv_insp:
        res.delivery_inspection = QualityInspectionResponse.model_validate(deliv_insp)

    return res
