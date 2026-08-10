"""
Automated Test for FIX 1 using FastAPI TestClient:
1. Register a new farmer account (requires certificate file upload logic).
2. Confirm farmer account is created in PENDING state (verified = False, status = 'pending', verification_status = 'pending_verification').
3. Confirm farmer CANNOT publish listings in PENDING state (returns 403 Forbidden).
4. Admin reviews & approves farmer certificate.
5. Confirm farmer account becomes ACTIVE / VERIFIED.
6. Confirm farmer CAN NOW publish listings successfully.
"""

import sys
import os
import uuid

sys.path.append('backend')
from main import app
from database import SessionLocal
from models.all_models import User, Farm, Product
from fastapi.testclient import TestClient

def test_fix1_flow():
    print("=" * 60)
    print("RUNNING AUTOMATED TEST FOR FIX 1: FARMER REGISTRATION & GATING")
    print("=" * 60)

    client = TestClient(app)
    db = SessionLocal()
    try:
        # 1. Register a new farmer
        unique_email = f"farmer_fix1_{uuid.uuid4().hex[:6]}@test.ie"
        reg_payload = {
            "email": unique_email,
            "password": "Password123!",
            "role": "farmer",
            "name": "Test Farmer Fix1",
            "phone": "+353871112233"
        }
        res = client.post("/api/auth/register", json=reg_payload)
        assert res.status_code == 200, f"Registration failed: {res.text}"
        farmer_data = res.json()
        token = farmer_data["access_token"]
        farmer_id = farmer_data["user_id"]
        headers = {"Authorization": f"Bearer {token}"}

        print(f"[OK] Step 1: Registered farmer '{unique_email}' (ID: {farmer_id[:8]})")

        # 2. Check DB status
        user_db = db.query(User).filter(User.id == farmer_id).first()
        farm_db = db.query(Farm).filter(Farm.user_id == farmer_id).first()

        assert user_db.status == "pending", f"Expected user.status 'pending', got '{user_db.status}'"
        assert not user_db.verified, "Expected user.verified False"
        assert farm_db.verification_status == "pending_verification", f"Expected farm verification_status 'pending_verification', got '{farm_db.verification_status}'"
        assert not farm_db.verified, "Expected farm.verified False"

        print("[OK] Step 2: Confirmed farmer is in PENDING state (verified=False, status='pending', verification_status='pending_verification')")

        # 3. Attempt to create listing as pending farmer (must fail with 403 Forbidden)
        dummy_img_path = "scratch/tomato_pile.jpg"
        with open(dummy_img_path, "rb") as f:
            files = {"image": ("tomato.jpg", f.read(), "image/jpeg")}
            data = {
                "product_type": "tomato",
                "variety": "Organic Roma",
                "production_date": "2026-08-09",
                "available_quantity": "50.0",
                "quantity_unit": "kg",
                "price_per_unit": "2.50",
                "is_bulk": "true",
                "hours_active": "24"
            }
            list_res = client.post(f"/api/farms/{farm_db.id}/products", headers=headers, data=data, files=files)

        assert list_res.status_code == 403, f"Expected 403 Forbidden for pending farmer listing creation, got {list_res.status_code}: {list_res.text}"
        print(f"[OK] Step 3: Verified pending farmer CANNOT create listing (Blocked with 403 Forbidden: {list_res.json()['detail']})")

        # 4. Admin approves farmer certificate
        admin_user = db.query(User).filter(User.role == "admin").first()
        if not admin_user:
            admin_user = User(email="admin_fix1@test.ie", password_hash="hash", role="admin", name="Admin", verified=True)
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

        from routers.auth import create_access_token
        admin_token = create_access_token({"sub": admin_user.id, "role": "admin"})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        approve_res = client.put(
            f"/api/admin/farms/{farm_db.id}/verify",
            headers=admin_headers,
            json={"verified": True, "note": "Approved by admin for FIX 1 test"}
        )
        assert approve_res.status_code == 200, f"Admin approval failed: {approve_res.text}"
        print("[OK] Step 4: Admin reviewed and APPROVED farmer certificate")

        # 5. Confirm DB state updated to verified
        db.refresh(user_db)
        db.refresh(farm_db)
        assert user_db.status == "verified", f"Expected user.status 'verified', got '{user_db.status}'"
        assert user_db.verified, "Expected user.verified True"
        assert farm_db.verification_status == "verified", f"Expected farm verification_status 'verified', got '{farm_db.verification_status}'"
        assert farm_db.verified, "Expected farm.verified True"

        print("[OK] Step 5: Confirmed farmer account and farm are now ACTIVE / VERIFIED")

        # 6. Attempt to create listing as approved farmer (must succeed)
        with open(dummy_img_path, "rb") as f:
            files = {"image": ("tomato.jpg", f.read(), "image/jpeg")}
            data = {
                "product_type": "tomato",
                "variety": "Organic Roma",
                "production_date": "2026-08-09",
                "available_quantity": "50.0",
                "quantity_unit": "kg",
                "price_per_unit": "2.50",
                "is_bulk": "true",
                "hours_active": "24"
            }
            succ_list_res = client.post(f"/api/farms/{farm_db.id}/products", headers=headers, data=data, files=files)

        assert succ_list_res.status_code == 200, f"Expected 200 OK after approval, got {succ_list_res.status_code}: {succ_list_res.text}"
        prod_data = succ_list_res.json()
        print(f"[OK] Step 6: Verified approved farmer CAN NOW publish listing successfully (Listing ID: {prod_data['id'][:8]})")

        print("=" * 60)
        print("FIX 1 TEST COMPLETED SUCCESSFULLY WITH ALL ASSERTIONS PASSED!")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    test_fix1_flow()
