"""
Geocoding and Haversine Distance service for OrganicLink.
Offline geocoding using seed/irish_locations.py.
"""

import math
from seed.irish_locations import IRISH_LOCATIONS, DEFAULT_LOCATION


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two points in kilometers
    using the Haversine formula.
    """
    R = 6371.0 # Earth radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return round(distance, 2)


def geocode_irish_location(eircode: str = None, town: str = None) -> tuple[float, float]:
    """
    Derives (latitude, longitude) from eircode or town.
    Checks eircode routing key first (e.g. 'T12' from 'T12 AB34'), then falls back to town.
    """
    # 1. Try Eircode routing key (first 3 chars)
    if eircode:
        clean_code = eircode.strip().lower().replace(" ", "")
        routing_key = clean_code[:3]
        if routing_key in IRISH_LOCATIONS:
            return IRISH_LOCATIONS[routing_key]

    # 2. Try town name
    if town:
        clean_town = town.strip().lower()
        if clean_town in IRISH_LOCATIONS:
            return IRISH_LOCATIONS[clean_town]
        
        # Substring match fallback
        for name, coords in IRISH_LOCATIONS.items():
            if len(name) > 3 and name in clean_town:
                return coords

    # Default fallback
    return DEFAULT_LOCATION
