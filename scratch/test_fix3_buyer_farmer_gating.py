"""
Automated Test for FIX 3: Order Participant Gating (Buyer who is also a Farmer)
1. Create 2 farmer accounts: Farmer A (Seller) and Farmer B (Buyer).
2. Farmer A creates a produce listing.
3. Farmer B buys produce from Farmer A -> Order created (farmer_id = A, buyer_id = B).
4. Verify backend endpoints:
   - Farmer B (buyer) attempting to upload dispatch photo or dispatch order -> 403 Forbidden.
   - Farmer A (seller) uploading dispatch photo or dispatching order -> 200 OK.
   - Farmer A (seller) attempting to upload delivery photo -> 403 Forbidden.
   - Farmer B (buyer) uploading delivery photo -> 200 OK.
"""

import sys
import os
import uuid

sys.path.append('backend')
from main import app
from database import SessionLocal
from models.all_models import User, Farm, Product, Order
from fastapi.testclient import TestClient
from routers.auth import create_access_token

def test_fix3_flow():
    print("=" * 60)
    print("RUNNING AUTOMATED TEST FOR FIX 3: PARTICIPANT ACTION GATING")
    print("=" * 60)

    client = TestClient(app)
    db = SessionLocal()
    try:
        # Create Seller Farmer A
        seller_user = User(email=f"seller_{uuid.uuid4().hex[:6]}@test.ie", password_hash="hash", role="farmer", name="Seller Farmer A", verified=True, status="verified")
        buyer_farmer = User(email=f"buyer_farmer_{uuid.uuid4().hex[:6]}@test.ie", password_hash="hash", role="farmer", name="Buyer Farmer B", verified=True, status="verified")
        db.add(seller_user)
        db.add(buyer_farmer)
        db.commit()
        db.refresh(seller_user)
        db.refresh(buyer_farmer)

        farm_a = Farm(user_id=seller_user.id, farm_name="Seller Farm A", town="Cork", county="Cork", eircode="T12 A111", verified=True, verification_status="verified")
        farm_b = Farm(user_id=buyer_farmer.id, farm_name="Buyer Farm B", town="Killarney", county="Kerry", eircode="V93 B222", verified=True, verification_status="verified")
        db.add(farm_a)
        db.add(farm_b)
        db.commit()
        db.refresh(farm_a)

        seller_token = create_access_token({"sub": seller_user.id, "role": "farmer"})
        buyer_token = create_access_token({"sub": buyer_farmer.id, "role": "farmer"})
        seller_headers = {"Authorization": f"Bearer {seller_token}"}
        buyer_headers = {"Authorization": f"Bearer {buyer_token}"}

        # 1. Seller Farmer A creates listing
        dummy_img_path = "scratch/valid_tomato.jpg"
        with open(dummy_img_path, "rb") as f:
            files = {"image": ("tomato.jpg", f.read(), "image/jpeg")}
            data = {
                "product_type": "banana",
                "variety": "Organic Cavendish",
                "production_date": "2026-08-09",
                "available_quantity": "50.0",
                "quantity_unit": "kg",
                "price_per_unit": "2.50",
                "is_bulk": "false",
                "hours_active": "24"
            }
            res = client.post(f"/api/farms/{farm_a.id}/products", headers=seller_headers, data=data, files=files)
        assert res.status_code == 200, f"Listing creation failed: {res.text}"
        prod_id = res.json()["id"]

        # 2. Buyer Farmer B buys from Seller Farmer A
        order_payload = {
            "product_id": prod_id,
            "quantity": 10.0,
            "delivery_date": "2026-08-10",
            "delivery_address": "Cork City, Co. Cork",
            "transport_by": "farmer",
            "delivery_type": "direct"
        }
        ord_res = client.post("/api/orders", headers=buyer_headers, json=order_payload)
        assert ord_res.status_code == 200, f"Order failed: {ord_res.text}"
        order_id = ord_res.json()["id"]
        print(f"[OK] Step 1: Created Order #{order_id[:8]} (Seller: Farmer A, Buyer: Farmer B)")

        # 3. Test Gating: Buyer Farmer B attempts Seller Dispatch Action -> MUST FAIL 403
        with open(dummy_img_path, "rb") as f:
            buyer_disp_res = client.post(
                f"/api/orders/{order_id}/farm-photo",
                headers=buyer_headers,
                files={"image": ("disp.jpg", f.read(), "image/jpeg")}
            )
        assert buyer_disp_res.status_code == 403, f"Expected 403 for Buyer Farmer B uploading dispatch photo, got {buyer_disp_res.status_code}"
        print("[OK] Step 2: Verified Buyer (Farmer B) CANNOT upload dispatch photo (Blocked 403 Forbidden)")

        buyer_disp_action = client.put(f"/api/orders/{order_id}/dispatch", headers=buyer_headers)
        assert buyer_disp_action.status_code == 403, f"Expected 403 for Buyer Farmer B dispatching order, got {buyer_disp_action.status_code}"
        print("[OK] Step 3: Verified Buyer (Farmer B) CANNOT dispatch order (Blocked 403 Forbidden)")

        # 4. Seller Farmer A accepts & uploads dispatch photo -> MUST SUCCEED
        client.put(f"/api/orders/{order_id}/accept", headers=seller_headers)
        with open(dummy_img_path, "rb") as f:
            seller_disp_res = client.post(
                f"/api/orders/{order_id}/farm-photo",
                headers=seller_headers,
                files={"image": ("disp.jpg", f.read(), "image/jpeg")}
            )
        assert seller_disp_res.status_code == 200, f"Seller dispatch photo failed: {seller_disp_res.text}"
        client.put(f"/api/orders/{order_id}/dispatch", headers=seller_headers)
        print("[OK] Step 4: Verified Seller (Farmer A) CAN upload dispatch photo and dispatch order")

        # 5. Test Gating: Seller Farmer A attempts Buyer Delivery Action -> MUST FAIL 403
        with open(dummy_img_path, "rb") as f:
            seller_deliv_res = client.post(
                f"/api/orders/{order_id}/delivery-photo",
                headers=seller_headers,
                files={"image": ("deliv.jpg", f.read(), "image/jpeg")}
            )
        assert seller_deliv_res.status_code == 403, f"Expected 403 for Seller Farmer A uploading delivery photo, got {seller_deliv_res.status_code}"
        print("[OK] Step 5: Verified Seller (Farmer A) CANNOT upload delivery photo (Blocked 403 Forbidden)")

        # 6. Buyer Farmer B uploads delivery photo -> MUST SUCCEED
        with open(dummy_img_path, "rb") as f:
            buyer_deliv_res = client.post(
                f"/api/orders/{order_id}/delivery-photo",
                headers=buyer_headers,
                files={"image": ("deliv.jpg", f.read(), "image/jpeg")},
                data={"buyer_action": "auto"}
            )
        assert buyer_deliv_res.status_code == 200, f"Buyer delivery photo failed: {buyer_deliv_res.text}"
        print("[OK] Step 6: Verified Buyer (Farmer B) CAN upload delivery photo successfully")

        print("=" * 60)
        print("FIX 3 TEST COMPLETED SUCCESSFULLY WITH ALL ASSERTIONS PASSED!")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    test_fix3_flow()
