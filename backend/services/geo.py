"""
Geocoding and Haversine Distance Service for OrganicLink.

Provides regional aggregation distance computation and offline Eircode / town lookup.
Computes great-circle distances across the Irish geographic coordinates matrix.

References:
- Sinnott, R. W. (1984). Virtues of the Haversine. Sky and Telescope, 68(2), 159.
- Department of Communications, Energy and Natural Resources (2015). Eircode System and Routing Key Matrix.
"""

import math
from seed.irish_locations import IRISH_LOCATIONS, DEFAULT_LOCATION


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two points in kilometers
    using the Haversine formula (Sinnott, 1984).
    """
    R = 6371.0 # WGS84 volumetric mean Earth radius in kilometers

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
    Derives (latitude, longitude) from Eircode routing key or Irish town name.
    Checks Eircode routing key prefix first (e.g. 'T12' from 'T12 AB34'), then falls back to town match.
    """
    # 1. Try Eircode routing key (first 3 chars)
    if eircode:
        clean_code = eircode.strip().lower().replace(" ", "")
        routing_key = clean_code[:3]
        if routing_key in IRISH_LOCATIONS:
            return IRISH_LOCATIONS[routing_key]

    # 2. Try town name lookup
    if town:
        clean_town = town.strip().lower()
        if clean_town in IRISH_LOCATIONS:
            return IRISH_LOCATIONS[clean_town]
        
        # Substring fuzzy match fallback
        for name, coords in IRISH_LOCATIONS.items():
            if len(name) > 3 and name in clean_town:
                return coords

    # Fallback to central Irish reference point (Athlone/Midlands)
    return DEFAULT_LOCATION
