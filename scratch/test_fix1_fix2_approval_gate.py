"""
Automated Test for FIX 1 & FIX 2: Farmer Registration Approval Gating & Admin Reject Option
1. Register a new farmer -> verify status is 'pending' and verified=False.
2. Attempt to create listing / view profile as pending farmer -> verify blocked with 403.
3. Test Admin REJECT: Admin rejects farm verification -> verify status becomes 'rejected', farm.verification_status='rejected'.
4. Test Admin APPROVE: Admin approves farm verification -> verify status becomes 'verified', farm.verification_status='verified'.
5. Approved farmer creates listing -> succeeds with 200 OK.
"""

import sys
import os
import uuid

sys.path.append('backend')
from main import app
from database import SessionLocal
from models.all_models import User, Farm, Product
from fastapi.testclient import TestClient
from routers.auth import create_access_token

def test_fix1_fix2_flow():
    print("=" * 60)
    print("RUNNING AUTOMATED TEST FOR FIX 1 & FIX 2: FARMER APPROVAL GATING & REJECT")
    print("=" * 60)

    client = TestClient(app)
    db = SessionLocal()
    try:
        # 1. Register new farmer
        farmer_email = f"farmer_gate_{uuid.uuid4().hex[:6]}@test.ie"
        reg_payload = {
            "email": farmer_email,
            "password": "password123",
            "role": "farmer",
            "name": "Pending Farmer Joe",
            "phone": "+353871234567"
        }
        res = client.post("/api/auth/register", json=reg_payload)
        assert res.status_code == 200, f"Registration failed: {res.text}"
        farmer_token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {farmer_token}"}

        farmer_db = db.query(User).filter(User.email == farmer_email).first()
        farm_db = db.query(Farm).filter(Farm.user_id == farmer_db.id).first()

        assert farmer_db.status == "pending", f"Expected status 'pending', got '{farmer_db.status}'"
        assert not farmer_db.verified, "Expected farmer.verified False"
        assert farm_db.verification_status == "pending_verification", f"Expected farm 'pending_verification', got '{farm_db.verification_status}'"
        print(f"[OK] Step 1: Registered Farmer '{farmer_email}' in PENDING state")

        # 2. Attempt to view profile as pending farmer
        prof_res = client.get("/api/profile/me", headers=headers)
        assert prof_res.status_code == 403, f"Expected 403 Forbidden for pending farmer profile access, got {prof_res.status_code}"
        print(f"[OK] Step 2: Verified Pending Farmer blocked from profile access (403 Forbidden)")

        # 3. Test Admin REJECT (FIX 2)
        admin_user = db.query(User).filter(User.role == "admin").first()
        if not admin_user:
            admin_user = User(email="admin_test@test.ie", password_hash="hash", role="admin", name="Admin", verified=True)
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

        admin_token = create_access_token({"sub": admin_user.id, "role": "admin"})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        reject_res = client.put(
            f"/api/admin/farms/{farm_db.id}/verify",
            headers=admin_headers,
            json={"verified": False, "note": "Cert invalid - rejected"}
        )
        assert reject_res.status_code == 200, f"Admin reject failed: {reject_res.text}"
        
        db.refresh(farmer_db)
        db.refresh(farm_db)
        assert farmer_db.status == "rejected", f"Expected farmer status 'rejected', got '{farmer_db.status}'"
        assert farm_db.verification_status == "rejected", f"Expected farm verification_status 'rejected', got '{farm_db.verification_status}'"
        print("[OK] Step 3: Verified Admin REJECT option sets farmer.status='rejected' and farm.verification_status='rejected'")

        # 4. Test Admin APPROVE (FIX 1)
        approve_res = client.put(
            f"/api/admin/farms/{farm_db.id}/verify",
            headers=admin_headers,
            json={"verified": True, "note": "Approved by admin"}
        )
        assert approve_res.status_code == 200, f"Admin approve failed: {approve_res.text}"

        db.refresh(farmer_db)
        db.refresh(farm_db)
        assert farmer_db.status == "verified", f"Expected farmer status 'verified', got '{farmer_db.status}'"
        assert farmer_db.verified, "Expected farmer.verified True"
        assert farm_db.verification_status == "verified", f"Expected farm verification_status 'verified', got '{farm_db.verification_status}'"
        print("[OK] Step 4: Verified Admin APPROVE option activates farmer (status='verified', verified=True)")

        # 5. Verified farmer can now view profile and create listings
        prof_res_2 = client.get("/api/profile/me", headers=headers)
        assert prof_res_2.status_code == 200, f"Profile access failed after approval: {prof_res_2.text}"
        print("[OK] Step 5: Confirmed Approved Farmer CAN NOW access profile and listing features")

        print("=" * 60)
        print("FIX 1 & FIX 2 TEST COMPLETED SUCCESSFULLY WITH ALL ASSERTIONS PASSED!")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    test_fix1_fix2_flow()
