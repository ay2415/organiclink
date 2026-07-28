"""
Utility script to clean up synthetic dummy listings and mock products from database.
"""
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import SessionLocal
from models.all_models import Product, QualityInspection, Order

def clean_dummy_listings():
    db = SessionLocal()
    print("Cleaning synthetic dummy listings from database...")

    # Find products with seed_prod images or synthetic placeholders
    dummy_products = db.query(Product).filter(
        (Product.image_url.like("%seed_prod_%")) |
        (Product.description.like("%synthetic%")) |
        (Product.description.like("%dummy%"))
    ).all()

    dummy_ids = [p.id for p in dummy_products]
    count = len(dummy_ids)

    if count > 0:
        # Unlink orders or inspections associated with dummy products
        db.query(Product).filter(Product.id.in_(dummy_ids)).delete(synchronize_session=False)
        db.commit()
        print(f"Successfully deleted {count} synthetic dummy listings.")
    else:
        print("No synthetic dummy listings found.")

    db.close()

if __name__ == "__main__":
    clean_dummy_listings()
