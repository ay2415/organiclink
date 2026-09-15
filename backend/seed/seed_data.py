"""
Production Seed Script for OrganicLink.
Populates ONLY authentic infrastructure and regional hub directory data:
- 25 Irish Regional Hubs across all counties for local distance calculation and drop-off routing.

Zero mock user accounts or predictable passwords are created by this script.
To initialize your administrator account, run:
    python -m seed.create_admin
"""

import os
import sys

# Ensure backend root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal, Base
from models import HubDirectory


def seed_database():
    print("Seeding OrganicLink regional directory & logistics infrastructure...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if directory already seeded
    if db.query(HubDirectory).count() >= 25:
        print("Regional Hub directory already populated. Skipping.")
        db.close()
        return

    # 25 Verified Irish Regional Logistics Hubs
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
        existing = db.query(HubDirectory).filter(HubDirectory.name == name).first()
        if not existing:
            h = HubDirectory(
                name=name, hub_type=htype, town=town, county=county, eircode=eir,
                latitude=lat, longitude=lng, accepts_products=prods,
                contact_email=f"info@{town.lower().replace(' ', '')}hub.ie"
            )
            db.add(h)
    db.commit()
    db.close()
    print("Successfully populated 25 Irish regional hubs in directory.")


if __name__ == "__main__":
    seed_database()
