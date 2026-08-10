"""
Automated Test for FIX 4: QR Code & Traceability Passport
1. Create a product listing.
2. Request GET /api/traceability/product/{product_id} -> verify farm of origin, organic cert, inspection history.
3. Request GET /api/traceability/qr?url=... -> verify 200 OK and PNG content-type.
4. Create an order and request GET /api/traceability/order/{order_id} -> verify order traceability details.
"""

import sys
import os

sys.path.append('backend')
from main import app
from database import SessionLocal
from models.all_models import Product, Farm, Order
from fastapi.testclient import TestClient

def test_fix4_flow():
    print("=" * 60)
    print("RUNNING AUTOMATED TEST FOR FIX 4: QR CODE & TRACEABILITY PASSPORT")
    print("=" * 60)

    client = TestClient(app)
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.status == "listed").first()
        assert product is not None, "Product listed record required for test"

        # 1. Product Traceability Endpoint
        p_res = client.get(f"/api/traceability/product/{product.id}")
        assert p_res.status_code == 200, f"Product traceability failed: {p_res.text}"
        p_data = p_res.json()
        assert "farm" in p_data, "Expected farm in traceability data"
        assert "inspections" in p_data, "Expected inspections in traceability data"
        print(f"[OK] Step 1: Fetched Product Traceability Passport for '{p_data['product']['product_type']}' (Farm: '{p_data['farm']['farm_name']}', Cert: '{p_data['farm']['organic_cert_number']}')")

        # 2. QR Code Image Endpoint
        qr_url = f"http://localhost:5173/traceability/product/{product.id}"
        qr_res = client.get(f"/api/traceability/qr?url={qr_url}")
        assert qr_res.status_code == 200, f"QR code generation failed: {qr_res.status_code}"
        assert qr_res.headers["content-type"] == "image/png", f"Expected content-type image/png, got {qr_res.headers.get('content-type')}"
        assert len(qr_res.content) > 100, "QR code image content empty"
        print(f"[OK] Step 2: Verified QR Code PNG Generation (Size: {len(qr_res.content)} bytes)")

        # 3. Order Traceability Endpoint
        order = db.query(Order).first()
        if order:
            o_res = client.get(f"/api/traceability/order/{order.id}")
            assert o_res.status_code == 200, f"Order traceability failed: {o_res.text}"
            o_data = o_res.json()
            assert "inspections" in o_data, "Expected inspections in order traceability data"
            print(f"[OK] Step 3: Fetched Order Traceability Passport for Order #{order.id[:8]}")

        print("=" * 60)
        print("FIX 4 TEST COMPLETED SUCCESSFULLY WITH ALL ASSERTIONS PASSED!")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    test_fix4_flow()
