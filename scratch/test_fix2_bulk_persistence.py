"""
Automated Test for FIX 2: Bulk Grading Mode Persistence Across Transaction Flow
1. Create a listing with is_bulk = True.
2. Place an order for that listing.
3. Accept & upload dispatch photo -> confirm grade_bulk() is auto-triggered.
4. Dispatch & upload delivery photo -> confirm grade_bulk() is auto-triggered.
"""

import sys
import os
import uuid

sys.path.append('backend')
from main import app
from database import SessionLocal
from models.all_models import User, Farm, Product, Order, QualityInspection
from fastapi.testclient import TestClient
from routers.auth import create_access_token

def test_fix2_flow():
    print("=" * 60)
    print("RUNNING AUTOMATED TEST FOR FIX 2: BULK MODE PERSISTENCE")
    print("=" * 60)

    client = TestClient(app)
    db = SessionLocal()
    try:
        farmer = db.query(User).filter(User.role == "farmer", User.verified == True).first()
        buyer = db.query(User).filter(User.role.in_(["consumer", "retailer", "restaurant"])).first()
        if not buyer:
            buyer = User(email="buyer_test_fix2@test.ie", password_hash="hash", role="consumer", name="Test Buyer", verified=True)
            db.add(buyer)
            db.commit()
            db.refresh(buyer)

        farm = db.query(Farm).filter(Farm.user_id == farmer.id).first()

        farmer_token = create_access_token({"sub": farmer.id, "role": farmer.role})
        buyer_token = create_access_token({"sub": buyer.id, "role": buyer.role})

        farmer_headers = {"Authorization": f"Bearer {farmer_token}"}
        buyer_headers = {"Authorization": f"Bearer {buyer_token}"}

        # 1. Create a bulk listing
        dummy_img_path = "scratch/valid_tomato.jpg"
        with open(dummy_img_path, "rb") as f:
            files = {"image": ("tomato.jpg", f.read(), "image/jpeg")}
            data = {
                "product_type": "tomato",
                "variety": "Organic Bulk Roma",
                "production_date": "2026-08-09",
                "available_quantity": "100.0",
                "quantity_unit": "kg",
                "price_per_unit": "2.00",
                "is_bulk": "true",
                "hours_active": "24"
            }
            res = client.post(f"/api/farms/{farm.id}/products", headers=farmer_headers, data=data, files=files)

        assert res.status_code == 200, f"Listing creation failed: {res.text}"
        prod = res.json()
        assert prod["is_bulk"] == True, "Expected product.is_bulk True"
        print(f"[OK] Step 1: Created Bulk Produce Listing (Product ID: {prod['id'][:8]}, is_bulk={prod['is_bulk']})")

        # 2. Place Order
        order_payload = {
            "product_id": prod["id"],
            "quantity": 20.0,
            "delivery_date": "2026-08-10",
            "delivery_address": "Cork City Market, Co. Cork",
            "transport_by": "farmer",
            "delivery_type": "direct"
        }
        ord_res = client.post("/api/orders", headers=buyer_headers, json=order_payload)
        assert ord_res.status_code == 200, f"Place order failed: {ord_res.text}"
        order = ord_res.json()
        order_id = order["id"]
        print(f"[OK] Step 2: Placed Order #{order_id[:8]} for Bulk Product")

        # 3. Farmer accepts order & uploads dispatch photo
        client.put(f"/api/orders/{order_id}/accept", headers=farmer_headers)

        disp_res = client.post(
            f"/api/orders/{order_id}/farm-photo",
            headers=farmer_headers,
            files={"image": ("disp.jpg", open(dummy_img_path, "rb"), "image/jpeg")}
        )
        print(f"[DEBUG] disp_res: status={disp_res.status_code}, text={disp_res.text}")
        assert disp_res.status_code == 200, f"Dispatch photo upload failed: {disp_res.text}"

        insp_db = db.query(QualityInspection).filter(QualityInspection.order_id == order_id, QualityInspection.inspection_level == "farm").first()
        assert insp_db is not None, "Dispatch inspection missing"
        assert insp_db.cv_results.get("is_bulk") == True, f"Expected is_bulk True in dispatch inspection cv_results, got {insp_db.cv_results}"
        print(f"[OK] Step 3: Verified Dispatch Inspection auto-executed in BULK mode (Score: {insp_db.quality_score}, Grade: {insp_db.quality_grade})")

        # 4. Dispatch order & Buyer uploads delivery photo
        client.put(f"/api/orders/{order_id}/dispatch", headers=farmer_headers)

        with open(dummy_img_path, "rb") as f:
            deliv_res = client.post(
                f"/api/orders/{order_id}/delivery-photo",
                headers=buyer_headers,
                files={"image": ("deliv.jpg", f.read(), "image/jpeg")},
                data={"buyer_action": "auto"}
            )
        assert deliv_res.status_code == 200, f"Delivery photo upload failed: {deliv_res.text}"

        deliv_insp_db = db.query(QualityInspection).filter(QualityInspection.order_id == order_id, QualityInspection.inspection_level == "delivery").first()
        assert deliv_insp_db is not None, "Delivery inspection missing"
        assert deliv_insp_db.cv_results.get("is_bulk") == True, f"Expected is_bulk True in delivery inspection cv_results, got {deliv_insp_db.cv_results}"
        print(f"[OK] Step 4: Verified Delivery Inspection auto-executed in BULK mode (Score: {deliv_insp_db.quality_score}, Grade: {deliv_insp_db.quality_grade})")

        print("=" * 60)
        print("FIX 2 TEST COMPLETED SUCCESSFULLY WITH ALL ASSERTIONS PASSED!")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    test_fix2_flow()
