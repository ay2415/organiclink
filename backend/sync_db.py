import sqlite3
import os
from database import engine, Base
from models.all_models import ProductType, Farm, User, Contract, Product, ProductionLog, Photo, QualityInspection, Order, Payment, RatingReview, Message, Notification, AuditLog, HubDirectory, AdminSetting

def sync_database():
    import sqlite3
    conn = sqlite3.connect("organiclink.db")
    cursor = conn.cursor()
    
    # Safely alter tables for new columns
    columns_to_add = [
        ("farms", "verification_status TEXT DEFAULT 'verified'"),
        ("contracts", "start_date DATE"),
        ("contracts", "end_date DATE"),
        ("orders", "buyer_payment_status TEXT DEFAULT 'pending'"),
        ("orders", "farmer_payment_status TEXT DEFAULT 'pending'"),
        ("orders", "payment_reference TEXT")
    ]
    for table, col_def in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
            conn.commit()
        except Exception:
            pass # Column already exists
    conn.close()

    Base.metadata.create_all(bind=engine)
    print("All SQLAlchemy tables created successfully.")

    # Seed product_types if empty
    from database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(ProductType).count() == 0:
            types = [
                ProductType(id="milk", name="Organic Raw Milk", category="dairy", default_unit="litre", default_log_type="daily", cv_gradable=False),
                ProductType(id="cheese", name="Organic Artisan Cheese", category="dairy", default_unit="kg", default_log_type="batch", cv_gradable=True),
                ProductType(id="tomato", name="Organic Tomato", category="vegetables", default_unit="kg", default_log_type="batch", cv_gradable=True),
                ProductType(id="onion", name="Organic Onion", category="vegetables", default_unit="kg", default_log_type="batch", cv_gradable=True),
                ProductType(id="apple", name="Organic Apple", category="fruit", default_unit="kg", default_log_type="batch", cv_gradable=True),
                ProductType(id="potato", name="Organic Potato", category="vegetables", default_unit="kg", default_log_type="batch", cv_gradable=True),
                ProductType(id="carrot", name="Organic Carrot", category="vegetables", default_unit="kg", default_log_type="batch", cv_gradable=True),
            ]
            db.add_all(types)
            db.commit()
            print("Seeded product_types table!")

        # Ensure farms are verified for demo
        farms = db.query(Farm).all()
        for farm in farms:
            farm.verification_status = "verified"
            farm.verified = True
        db.commit()
        print("Updated farm verification status to 'verified'!")

    finally:
        db.close()

if __name__ == "__main__":
    sync_database()
