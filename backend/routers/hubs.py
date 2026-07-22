"""
Directory Hubs router for OrganicLink.
Ranks seeded Irish organic buyer hubs/processors by Haversine distance from a farm.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import HubDirectory, Farm
from schemas.schemas import HubDirectoryResponse
from services.geo import haversine_distance

router = APIRouter(prefix="/api/hubs", tags=["Hubs Directory"])


@router.get("", response_model=List[HubDirectoryResponse])
def list_hubs(
    county: Optional[str] = Query(None),
    hub_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(HubDirectory)
    if county:
        query = query.filter(HubDirectory.county.lower() == county.lower())
    if hub_type:
        query = query.filter(HubDirectory.hub_type == hub_type.lower())

    return query.all()


@router.get("/nearest", response_model=List[HubDirectoryResponse])
def get_nearest_hubs(
    farm_id: Optional[str] = Query(None),
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    limit: int = Query(10),
    db: Session = Depends(get_db)
):
    ref_lat = lat
    ref_lng = lng

    if farm_id:
        farm = db.query(Farm).filter(Farm.id == farm_id).first()
        if farm:
            ref_lat = farm.latitude
            ref_lng = farm.longitude

    if ref_lat is None or ref_lng is None:
        ref_lat = 53.3498 # Dublin fallback
        ref_lng = -6.2603

    hubs = db.query(HubDirectory).all()

    results = []
    for h in hubs:
        dist_km = haversine_distance(ref_lat, ref_lng, h.latitude, h.longitude)
        h_dict = HubDirectoryResponse.model_validate(h)
        h_dict.distance_km = dist_km
        results.append(h_dict)

    results.sort(key=lambda x: x.distance_km)
    return results[:limit]
