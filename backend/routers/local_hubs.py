"""
Local City Hubs & Common Collection Drop-off Points router for OrganicLink.
Provides common pickup hubs by city/county for individual buyers and small batch trades.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.all_models import HubDirectory, Farm

router = APIRouter(prefix="/api/hubs", tags=["Local Hubs & Collection Points"])

LOCAL_COLLECTION_POINTS = [
    {
        "id": "hub-cork-central",
        "name": "Cork Central Organic Drop-Off Depot (Grand Parade)",
        "county": "Cork",
        "town": "Cork City",
        "address": "Grand Parade Farmers Market Depot, Cork City",
        "eircode": "T12 K863",
        "operating_hours": "Mon-Sat 08:00 - 18:00"
    },
    {
        "id": "hub-cork-bandon",
        "name": "Bandon Local Farmers Collection Hub",
        "county": "Cork",
        "town": "Bandon",
        "address": "Main Street Cooperative Depot, Bandon, Co. Cork",
        "eircode": "P72 V220",
        "operating_hours": "Mon-Fri 08:30 - 17:30"
    },
    {
        "id": "hub-galway-central",
        "name": "Galway Local Food Common Hub (Eyre Square)",
        "county": "Galway",
        "town": "Galway City",
        "address": "Eyre Square Central Depot, Galway City",
        "eircode": "H91 H602",
        "operating_hours": "Mon-Sat 08:00 - 18:00"
    },
    {
        "id": "hub-dublin-central",
        "name": "Dublin City Organic Cooperative Pickup Hub",
        "county": "Dublin",
        "town": "Dublin City",
        "address": "Smithfield Food Market Depot, Dublin 7",
        "eircode": "D07 X250",
        "operating_hours": "Mon-Sat 07:30 - 19:00"
    },
    {
        "id": "hub-limerick-central",
        "name": "Limerick Milk Market Common Drop-Off Depot",
        "county": "Limerick",
        "town": "Limerick City",
        "address": "Milk Market Depot, Mallow Street, Limerick",
        "eircode": "V94 P521",
        "operating_hours": "Mon-Sat 08:00 - 17:00"
    },
    {
        "id": "hub-waterford-central",
        "name": "Waterford Local Produce Drop-Off Hub",
        "county": "Waterford",
        "town": "Waterford City",
        "address": "Quayside Cooperative Depot, Waterford",
        "eircode": "X91 E120",
        "operating_hours": "Mon-Fri 09:00 - 17:00"
    }
]


@router.get("/collection-points")
def get_collection_points(
    county: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    points = LOCAL_COLLECTION_POINTS
    if county:
        c_lower = county.lower().strip()
        points = [p for p in points if p["county"].lower() == c_lower]

    return points
