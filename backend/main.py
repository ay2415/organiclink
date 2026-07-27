"""
OrganicLink FastAPI Main Application Entrypoint.
Serves OpenAPI docs at /docs.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine, Base
from config import settings
from cv.inference import get_inference_engine
from services.documents import UPLOADS_DIR

# Import all routers
from routers.auth import router as auth_router
from routers.farms import router as farms_router
from routers.contracts import router as contracts_router
from routers.products import router as products_router
from routers.quality import router as quality_router
from routers.orders import router as orders_router
from routers.payments import router as payments_router
from routers.ratings import router as ratings_router
from routers.hubs import router as hubs_router
from routers.demand import router as demand_router
from routers.messages import router as messages_router
from routers.notifications import router as notifications_router
from routers.admin import router as admin_router
from routers.production_logs import router as production_logs_router

app = FastAPI(
    title="OrganicLink API",
    description="Irish Organic Farm Surplus Marketplace with Computer Vision Quality Grading",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory for static image/PDF access
os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=UPLOADS_DIR), name="static_uploads")
app.mount("/static", StaticFiles(directory=UPLOADS_DIR), name="static")

# Include Routers
app.include_router(auth_router)
app.include_router(farms_router)
app.include_router(contracts_router)
app.include_router(products_router)
app.include_router(quality_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(ratings_router)
app.include_router(hubs_router)
app.include_router(demand_router)
app.include_router(messages_router)
app.include_router(notifications_router)
app.include_router(admin_router)
app.include_router(production_logs_router)


@app.on_event("startup")
def startup_event():
    print("Initializing Database Tables...")
    Base.metadata.create_all(bind=engine)

    print("Initializing Computer Vision Quality Grading Model...")
    try:
        engine_inst = get_inference_engine()
        print("CV Inference Engine Ready.")
    except Exception as e:
        print(f"Warning: CV Inference Engine delayed initialization: {e}")


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "app": "OrganicLink API",
        "version": "1.0.0",
        "variance_tolerance_percent": settings.VARIANCE_TOLERANCE_PERCENT
    }
