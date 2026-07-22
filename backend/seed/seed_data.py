"""
Seed script for OrganicLink.
Populates realistic demo data:
- 1 Admin
- 8 Organic Farmers (including canonical Cork onion farmer: 100kg yield, 80kg contract, 20kg surplus)
- 10 Buyers across all 5 buyer roles
- 25 Seeded Hubs in directory across Ireland
- 20 Active Product Listings graded by the real CV engine
- 12 Orders across state machine (including 1 open disputed order with > 10% variance)
"""

import os
import sys
import uuid
import random
from datetime import datetime, date, timedelta
from PIL import Image, ImageDraw

# Ensure backend root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal, Base
from models import (
    User, Farm, ProductionHistory, Contract, Product, QualityInspection,
    Order, Payment, RatingReview, Message, Notification, AuditLog, HubDirectory
)
from routers.auth import get_password_hash
from cv.inference import get_inference_engine
from cv.grading import compute_variance
from services.geo import geocode_irish_location
from services.documents import UPLOADS_DIR, generate_invoice_pdf


def generate_seed_image(filename: str, color=(200, 80, 50), defects=0) -> str:
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    filepath = os.path.join(UPLOADS_DIR, filename)
    if os.path.exists(filepath):
        return f"/static/uploads/{filename}"

    img = Image.new("RGB", (300, 300), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    # Produce body
    draw.ellipse([30, 30, 270, 270], fill=color)

    # Defect spots
    for _ in range(defects):
        sx = random.randint(50, 230)
        sy = random.randint(50, 230)
        sr = random.randint(8, 20)
        draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(40, 30, 20))

    img.save(filepath)
    return f"/static/uploads/{filename}"


def seed_database():
    print("Seeding OrganicLink database...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if already seeded
    if db.query(User).filter(User.email == "admin@organiclink.ie").first():
        print("Database already seeded. Skipping.")
        db.close()
        return

    cv_engine = get_inference_engine()

    # 1. Admin
    admin_pw = get_password_hash("Admin123!")
    user_pw = get_password_hash("Password123!")

    admin = User(
        email="admin@organiclink.ie",
        password_hash=admin_pw,
        role="admin",
        name="OrganicLink Admin",
        phone="+353 1 496 0000",
        verified=True
    )
    db.add(admin)
    db.commit()

    # 2. 8 Farmers
    farmer_data = [
        {"email": "farmer@corkorganic.ie", "name": "Sean O'Mahony", "farm_name": "Glenbeg Organic Farm", "town": "Bandon", "county": "Cork", "eircode": "T56 AB12", "type": "produce", "cert": "IOA-10842"},
        {"email": "galway.dairy@organic.ie", "name": "Aoife Flaherty", "farm_name": "Corrib Organic Dairy", "town": "Tuam", "county": "Galway", "eircode": "H91 CD34", "type": "dairy", "cert": "OT-20491"},
        {"email": "tipp.produce@organic.ie", "name": "Liam Ryan", "farm_name": "Golden Vale Organic Produce", "town": "Nenagh", "county": "Tipperary", "eircode": "E41 EF56", "type": "produce", "cert": "IOA-11029"},
        {"email": "kildare.farm@organic.ie", "name": "Ciara Walsh", "farm_name": "Curragh Organic Haven", "town": "Naas", "county": "Kildare", "eircode": "W91 GH78", "type": "mixed", "cert": "IOA-10582"},
        {"email": "cavan.organics@organic.ie", "name": "Padraig Brady", "farm_name": "Lough Erne Organic Farm", "town": "Cavan", "county": "Cavan", "eircode": "H12 JK90", "type": "produce", "cert": "OT-20184"},
        {"email": "limerick.dairy@organic.ie", "name": "Siobhan Kelly", "farm_name": "Shannon Valley Organic Dairy", "town": "Limerick", "county": "Limerick", "eircode": "V94 LM12", "type": "dairy", "cert": "IOA-11492"},
        {"email": "waterford.orchard@organic.ie", "name": "Cormac Power", "farm_name": "Comeragh Organic Orchards", "town": "Dungarvan", "county": "Waterford", "eircode": "X35 NP34", "type": "produce", "cert": "OT-20819"},
        {"email": "clare.organics@organic.ie", "name": "Eimear O'Brien", "farm_name": "Burren Bio Organic Farm", "town": "Ennis", "county": "Clare", "eircode": "V95 QR56", "type": "mixed", "cert": "IOA-10928"}
    ]

    farmers = []
    farms = []
    for fd in farmer_data:
        u = User(email=fd["email"], password_hash=user_pw, role="farmer", name=fd["name"], phone="+353 87 123 4567", verified=True)
        db.add(u)
        db.commit()
        db.refresh(u)
        farmers.append(u)

        lat, lng = geocode_irish_location(eircode=fd["eircode"], town=fd["town"])
        f = Farm(
            user_id=u.id, farm_name=fd["farm_name"], town=fd["town"], county=fd["county"], eircode=fd["eircode"],
            latitude=lat, longitude=lng, size_hectares=25.0, produce_list=["onion", "milk", "apple", "potato", "carrot"],
            organic_cert_body="Irish Organic Association" if "IOA" in fd["cert"] else "Organic Trust",
            organic_cert_number=fd["cert"], cert_issue_date=date(2024, 1, 1), cert_expiry_date=date(2027, 12, 31),
            farm_type=fd["type"], description=f"Premium 100% certified organic farm based in {fd['town']}, Co. {fd['county']}.",
            reputation_score=88.5, total_orders_completed=14, average_quality_score=91.2, verified=True
        )
        db.add(f)
        db.commit()
        db.refresh(f)
        farms.append(f)

    # CANONICAL ONION FARMER (Cork Farm)
    cork_farm = farms[0]
    # Production history: 100kg/month onions produced
    for yr in [2024, 2025, 2026]:
        for mth in range(1, 13):
            ph = ProductionHistory(farm_id=cork_farm.id, product_type="onion", year=yr, month=mth, quantity=100.0, unit="kg")
            db.add(ph)
    # Active contract: 80kg/month committed
    c1 = Contract(
        farm_id=cork_farm.id, contract_name="Processor Annual Onion Supply", hub_name="Bandon Food Aggregators",
        product_type="onion", committed_quantity=80.0, quantity_unit="kg", period="month", price_per_unit=1.80,
        status="active", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)
    )
    db.add(c1)
    db.commit()

    # Seed production history & contracts for other farms
    for f in farms[1:]:
        prod_type = "milk" if f.farm_type == "dairy" else "apple"
        for yr in [2024, 2025, 2026]:
            ph = ProductionHistory(farm_id=f.id, product_type=prod_type, year=yr, month=6, quantity=500.0, unit="litre" if prod_type == "milk" else "kg")
            db.add(ph)
        ct = Contract(
            farm_id=f.id, contract_name=f"{prod_type.title()} Offtake Agreement", hub_name="Irish Organic Dairy Co",
            product_type=prod_type, committed_quantity=350.0, quantity_unit="litre" if prod_type == "milk" else "kg",
            period="month", price_per_unit=2.10, status="active"
        )
        db.add(ct)
    db.commit()

    # 3. 10 Buyers
    buyer_configs = [
        ("consumer1@organic.ie", "consumer", "Mary Fitzgerald"),
        ("consumer2@organic.ie", "consumer", "Patrick Connolly"),
        ("retail1@farmshop.ie", "retailer", "Bandon Organic Farm Shop"),
        ("retail2@deli.ie", "retailer", "Galway Green Deli"),
        ("rest1@bistro.ie", "restaurant", "Farm-to-Fork Bistro Cork"),
        ("rest2@eats.ie", "restaurant", "The Wild Plum Restaurant Dublin"),
        ("inst1@school.ie", "institution", "St. Patrick's College Canteen"),
        ("inst2@hospital.ie", "institution", "Mercy Hospital Kitchen"),
        ("mfg1@processor.ie", "manufacturer", "Kerry Organic Foods Ltd"),
        ("mfg2@packers.ie", "manufacturer", "Irish Organic Packers Aggregator")
    ]

    buyers = []
    for email, role, name in buyer_configs:
        u = User(email=email, password_hash=user_pw, role=role, name=name, phone="+353 86 987 6543", verified=True)
        db.add(u)
        db.commit()
        db.refresh(u)
        buyers.append(u)

    # 4. 25 Seeded Hubs in directory
    hub_records = [
        ("Bandon Food Aggregators", "manufacturer", "Bandon", "Cork", "T56 AB12", 51.7469, -8.7425, ["onion", "potato", "carrot"]),
        ("Irish Organic Dairy Co", "processor", "Mallow", "Cork", "T12 XY89", 52.1389, -8.6433, ["milk", "cheese"]),
        ("Galway Green Deli & Hub", "store", "Galway", "Galway", "H91 CD34", 53.2707, -9.0568, ["onion", "apple", "potato"]),
        ("Midleton Organic Store", "store", "Midleton", "Cork", "T56 GH12", 51.9153, -8.1750, ["apple", "cheese", "milk"]),
        ("Naas Bio Farm Shop", "store", "Naas", "Kildare", "W91 AB34", 53.2158, -6.6669, ["carrot", "potato", "onion"]),
        ("Nenagh Artisan Pantry", "restaurant", "Nenagh", "Tipperary", "E41 JK56", 52.8619, -8.1969, ["apple", "cheese"]),
        ("Cavan Fresh Organic Hub", "processor", "Cavan", "Cavan", "H12 OP78", 53.9908, -7.3606, ["milk", "potato"]),
        ("Limerick Farm Aggregators", "manufacturer", "Limerick", "Limerick", "V94 ST90", 52.6638, -8.6267, ["milk", "onion"]),
        ("Dungarvan Organic Kitchen", "restaurant", "Dungarvan", "Waterford", "X35 UV12", 52.0883, -7.6256, ["apple", "carrot"]),
        ("Ennis Bio Market", "store", "Ennis", "Clare", "V95 WX34", 52.8463, -8.9806, ["cheese", "potato"]),
        ("Dublin Central Organic Hub", "store", "Dublin", "Dublin", "D01 AB12", 53.3498, -6.2603, ["onion", "milk", "apple"]),
        ("Kilkenny Organic Depot", "processor", "Kilkenny", "Kilkenny", "R95 CD56", 52.6541, -7.2448, ["cheese", "milk"]),
        ("Tralee Green Market", "store", "Tralee", "Kerry", "V92 EF78", 52.2704, -9.7026, ["apple", "onion"]),
        ("Wexford Organic Aggregators", "manufacturer", "Wexford", "Wexford", "Y35 GH90", 52.3369, -6.4633, ["potato", "carrot"]),
        ("Athlone Bio Foods", "processor", "Athlone", "Westmeath", "N37 JK12", 53.4239, -7.9406, ["milk", "cheese"]),
        ("Sligo Artisan Co-op", "store", "Sligo", "Sligo", "F91 LM34", 54.2711, -8.4739, ["potato", "onion"]),
        ("Dundalk Organic Pantry", "restaurant", "Dundalk", "Louth", "A91 NP56", 54.0039, -6.4022, ["apple", "cheese"]),
        ("Castlebar Farm Produce", "store", "Castlebar", "Mayo", "F23 QR78", 53.8500, -9.3000, ["carrot", "potato"]),
        ("Navan Bio Aggregator", "manufacturer", "Navan", "Meath", "C15 ST90", 53.6528, -6.6814, ["onion", "milk"]),
        ("Portlaoise Organic Hub", "processor", "Portlaoise", "Laois", "R32 UV12", 53.0344, -7.2997, ["potato", "milk"]),
        ("Clonmel Fresh Foods", "store", "Clonmel", "Tipperary", "E91 WX34", 52.3550, -7.7039, ["apple", "onion"]),
        ("Letterkenny Bio Depot", "processor", "Letterkenny", "Donegal", "F92 YZ56", 54.9558, -7.7347, ["milk", "cheese"]),
        ("Tullamore Organic Co", "manufacturer", "Tullamore", "Offaly", "R35 AB78", 53.2739, -7.4914, ["onion", "carrot"]),
        ("Wicklow Farm Kitchen", "restaurant", "Wicklow", "Wicklow", "A67 CD90", 52.9808, -6.0444, ["apple", "cheese"]),
        ("Carlow Organic Aggregator", "processor", "Carlow", "Carlow", "R93 EF12", 52.8365, -6.9261, ["potato", "milk"])
    ]

    for name, htype, town, county, eir, lat, lng, prods in hub_records:
        h = HubDirectory(name=name, hub_type=htype, town=town, county=county, eircode=eir, latitude=lat, longitude=lng, accepts_products=prods, contact_email=f"info@{town.lower().replace(' ', '')}hub.ie")
        db.add(h)
    db.commit()

    # 5. 20 Active Listings graded via real CV pipeline
    produce_types = ["onion", "milk", "apple", "potato", "carrot", "cheese"]
    products = []
    for i in range(20):
        farm = random.choice(farms)
        ptype = produce_types[i % len(produce_types)]
        qty = random.choice([20.0, 50.0, 100.0, 150.0])
        unit = "kg" if ptype not in ["milk"] else "litre"
        price = round(random.uniform(1.20, 4.50), 2)

        # Generate image file
        img_url = generate_seed_image(f"seed_prod_{i}.png", color=(random.randint(100, 220), random.randint(100, 200), random.randint(50, 150)), defects=random.choice([0, 1, 2]))
        img_abs = os.path.join(UPLOADS_DIR, f"seed_prod_{i}.png")

        # Run through CV inference engine
        cv_res = cv_engine.analyze_image(img_abs)

        insp = QualityInspection(
            inspection_level="farm", image_url=img_url, cv_results=cv_res["cv_results"],
            quality_score=cv_res["quality_score"], quality_grade=cv_res["quality_grade"],
            defects_detected=cv_res["defects_detected"], model_confidence=cv_res["model_confidence"],
            model_version=cv_res["model_version"], inspector_id=farm.user_id
        )
        db.add(insp)
        db.commit()
        db.refresh(insp)

        prod = Product(
            farm_id=farm.id, product_type=ptype, variety="Organic Premium Grade", production_date=date.today() - timedelta(days=random.randint(1, 5)),
            available_quantity=qty, quantity_unit=unit, price_per_unit=price, buyer_types_open_to=["consumer", "retailer", "restaurant", "institution", "manufacturer"],
            provides_transport=random.choice([True, False]), image_url=img_url, quality_grade=cv_res["quality_grade"],
            quality_score=cv_res["quality_score"], quality_inspection_id=insp.id, demand_score=random.uniform(65.0, 92.0),
            demand_is_estimate=True, status="listed", description=f"Fresh 100% certified organic {ptype} surplus available directly from {farm.farm_name}."
        )
        db.add(prod)
        db.commit()
        db.refresh(prod)

        insp.product_id = prod.id
        db.commit()
        products.append(prod)

    # 6. 12 Orders across state machine (including 1 DISPUTED with variance > 10%)
    # Order 1: Disputed order (variance > 10%)
    disputed_farm_img = generate_seed_image("dispute_farm.png", color=(210, 160, 50), defects=0) # score ~90
    disputed_deliv_img = generate_seed_image("dispute_deliv.png", color=(100, 80, 40), defects=8) # score ~55

    insp_farm_disp = QualityInspection(inspection_level="farm", image_url=disputed_farm_img, quality_score=92.0, quality_grade="A", defects_detected=[], cv_results={"colour_vibrancy": 88.0, "colour_uniformity": 92.0, "brightness": 85.0, "defect_coverage_percent": 1.2})
    insp_deliv_disp = QualityInspection(inspection_level="delivery", image_url=disputed_deliv_img, quality_score=62.0, quality_grade="C", defects_detected=["surface_blemishes", "discolouration"], cv_results={"colour_vibrancy": 55.0, "colour_uniformity": 58.0, "brightness": 50.0, "defect_coverage_percent": 14.5})

    db.add(insp_farm_disp)
    db.add(insp_deliv_disp)
    db.commit()

    dispute_ord = Order(
        product_id=products[0].id, farmer_id=farmers[0].id, buyer_id=buyers[4].id, # Restaurant buyer
        quantity=50.0, quantity_unit="kg", price_per_unit=2.00, total_price=100.0,
        delivery_date=date.today(), delivery_address="Wild Plum Restaurant, Cork", transport_by="farmer",
        status="disputed", farm_inspection_id=insp_farm_disp.id, delivery_inspection_id=insp_deliv_disp.id,
        quality_variance_percent=32.61, variance_acceptable=False, dispute_flag=True, dispute_status="open",
        dispute_reason="Quality dropped by 32.61% in transit (tolerance is ±10.0%). Surface blemishes and discolouration detected on delivery."
    )
    db.add(dispute_ord)
    db.commit()

    pay_disp = Payment(order_id=dispute_ord.id, farmer_id=farmers[0].id, buyer_id=buyers[4].id, amount=100.0, currency="EUR", payment_method="platform_mock", due_date=date.today() + timedelta(days=14), status="held")
    db.add(pay_disp)
    db.commit()

    log_audit_event(db, action="order_disputed", actor_id=buyers[4].id, actor_role="restaurant", order_id=dispute_ord.id, details={"variance_percent": 32.61})

    # Orders 2 & 3: Completed with ratings
    for k in range(2):
        comp_ord = Order(
            product_id=products[k+1].id, farmer_id=farmers[k+1].id, buyer_id=buyers[k].id,
            quantity=20.0, quantity_unit="kg", price_per_unit=2.50, total_price=50.0,
            delivery_date=date.today() - timedelta(days=5), delivery_address="12 Main St, Ireland",
            transport_by="farmer", status="completed", farm_inspection_id=products[k+1].quality_inspection_id,
            quality_variance_percent=2.1, variance_acceptable=True, dispute_flag=False
        )
        db.add(comp_ord)
        db.commit()

        rr1 = RatingReview(order_id=comp_ord.id, rater_id=buyers[k].id, ratee_id=farmers[k+1].id, rating_stars=5, review_text="Exceptional organic produce! Quality exceeded expectation.")
        rr2 = RatingReview(order_id=comp_ord.id, rater_id=farmers[k+1].id, ratee_id=buyers[k].id, rating_stars=5, review_text="Prompt payment and smooth communication.")
        db.add(rr1)
        db.add(rr2)
        db.commit()

    # Order 4: Negotiating
    neg_ord = Order(
        product_id=products[3].id, farmer_id=farmers[3].id, buyer_id=buyers[2].id,
        quantity=80.0, quantity_unit="kg", price_per_unit=2.20, total_price=176.0,
        delivery_date=date.today() + timedelta(days=3), delivery_address="Farm Shop Bandon",
        status="negotiating", negotiation_history=[
            {"action": "counter_offer", "actor": buyers[2].name, "role": buyers[2].role, "quantity": 80.0, "price_per_unit": 2.20, "message": "Can you offer a 10% discount for bulk 80kg?"}
        ]
    )
    db.add(neg_ord)

    # Order 5: Pending
    pend_ord = Order(
        product_id=products[4].id, farmer_id=farmers[4].id, buyer_id=buyers[3].id,
        quantity=30.0, quantity_unit="kg", price_per_unit=3.00, total_price=90.0,
        delivery_date=date.today() + timedelta(days=4), delivery_address="Green Deli Galway", status="pending"
    )
    db.add(pend_ord)

    # Order 6: Accepted (awaiting farm photo)
    acc_ord = Order(
        product_id=products[5].id, farmer_id=farmers[5].id, buyer_id=buyers[5].id,
        quantity=40.0, quantity_unit="kg", price_per_unit=2.80, total_price=112.0,
        delivery_date=date.today() + timedelta(days=2), delivery_address="Wild Plum Dublin", status="accepted"
    )
    db.add(acc_ord)

    # Order 7: In Transit
    trans_ord = Order(
        product_id=products[6].id, farmer_id=farmers[6].id, buyer_id=buyers[6].id,
        quantity=100.0, quantity_unit="litre", price_per_unit=1.90, total_price=190.0,
        delivery_date=date.today() + timedelta(days=1), delivery_address="St. Patrick College Canteen",
        status="in_transit", farm_inspection_id=products[6].quality_inspection_id
    )
    db.add(trans_ord)

    # Orders 8-12: Delivered / Paid
    for m in range(7, 12):
        d_ord = Order(
            product_id=products[m].id, farmer_id=farmers[m % len(farmers)].id, buyer_id=buyers[m % len(buyers)].id,
            quantity=25.0, quantity_unit="kg", price_per_unit=2.40, total_price=60.0,
            delivery_date=date.today() - timedelta(days=2), delivery_address="Ireland Address",
            status="delivered", farm_inspection_id=products[m].quality_inspection_id,
            quality_variance_percent=1.5, variance_acceptable=True
        )
        db.add(d_ord)
        db.commit()
        p = Payment(order_id=d_ord.id, farmer_id=d_ord.farmer_id, buyer_id=d_ord.buyer_id, amount=60.0, due_date=date.today() + timedelta(days=12), status="pending")
        db.add(p)
        db.commit()

    db.close()
    print("Database seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
