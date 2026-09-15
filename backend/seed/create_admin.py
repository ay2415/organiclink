"""
Secure One-Time Admin Setup Script for OrganicLink.
Creates the primary system administrator account using environment variables.

Usage:
    python -m seed.create_admin

Required Environment Variables (in .env or system environment):
    ADMIN_EMAIL       - Administrator login email (e.g. admin@yourdomain.com)
    ADMIN_PASSWORD    - Strong administrator password (minimum 8 characters)
    ADMIN_NAME        - (Optional) Administrator display name
    ADMIN_PHONE       - (Optional) Administrator contact phone
"""

import os
import sys

# Ensure backend root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal, Base
from models import User
from routers.auth import get_password_hash
from config import settings


def create_admin():
    print("=" * 60)
    print("OrganicLink Administrator Account Initialization")
    print("=" * 60)

    admin_email = os.getenv("ADMIN_EMAIL") or getattr(settings, "ADMIN_EMAIL", None)
    admin_password = os.getenv("ADMIN_PASSWORD") or getattr(settings, "ADMIN_PASSWORD", None)
    admin_name = os.getenv("ADMIN_NAME", "OrganicLink Administrator")
    admin_phone = os.getenv("ADMIN_PHONE", "+353 1 000 0000")

    if not admin_email or not admin_password:
        print("\n[ERROR] Missing required administrator configuration!")
        print("Please set the following environment variables in your server .env file:")
        print("  ADMIN_EMAIL=your_admin_email@example.com")
        print("  ADMIN_PASSWORD=YourStrongSecretPassword")
        print("\nExample:")
        print("  export ADMIN_EMAIL=admin@organiclink.ie")
        print("  export ADMIN_PASSWORD=YourSecurePassword123!")
        print("  python -m seed.create_admin\n")
        sys.exit(1)

    if len(admin_password) < 8:
        print("\n[ERROR] ADMIN_PASSWORD must be at least 8 characters long for security.")
        sys.exit(1)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    existing = db.query(User).filter(User.email == admin_email.strip().lower()).first()
    if existing:
        print(f"\n[NOTICE] Account with email '{admin_email}' already exists.")
        if existing.role != "admin":
            existing.role = "admin"
            existing.verified = True
            db.commit()
            print(f"[SUCCESS] Upgraded '{admin_email}' to administrator role.")
        else:
            print("[INFO] Administrator account is already active.")
        db.close()
        return

    admin_user = User(
        email=admin_email.strip().lower(),
        password_hash=get_password_hash(admin_password),
        role="admin",
        name=admin_name,
        phone=admin_phone,
        verified=True,
        status="verified"
    )

    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    db.close()

    print(f"\n[SUCCESS] Administrator account created successfully!")
    print(f"Email: {admin_email}")
    print(f"Role:  admin")
    print(f"Status: verified (Full system arbitration & governance access granted)\n")


if __name__ == "__main__":
    create_admin()
