"""
Nearby airport utilities.
Uses the Haversine formula to find airports within a given radius.
"""
import math
import logging

log = logging.getLogger(__name__)

# Hard limits
MAX_NEARBY_AIRPORTS = 3
NEARBY_RADIUS_KM    = 100


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two points
    on Earth using the Haversine formula.
    Returns distance in kilometres.
    """
    R = 6371  # Earth radius in km

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))

    return R * c


def get_nearby_airports(iata_code, radius_km=NEARBY_RADIUS_KM,
                        max_results=MAX_NEARBY_AIRPORTS):
    """
    Find active airports within radius_km of the given IATA code.
    Returns list of Airport objects, sorted by:
      1. airport_type (large first)
      2. distance (closest first)
    Excludes the origin airport itself.
    Caps at max_results.
    """
    from app.models import Airport

    origin = Airport.query.filter_by(
        iata_code=iata_code,
        is_active=True
    ).first()

    if not origin or origin.latitude is None or origin.longitude is None:
        log.debug("No coordinates for %s — skipping nearby search", iata_code)
        return []

    # Get all active large airports with coordinates
    # Large airports only — medium/small airports are unlikely
    # to have scheduled international services Duffel can price
    candidates = Airport.query.filter(
        Airport.is_active    == True,
        Airport.iata_code    != iata_code,
        Airport.latitude     != None,
        Airport.longitude    != None,
        Airport.airport_type == "large_airport",
    ).all()

    nearby = []
    for airport in candidates:
        dist = haversine_km(
            origin.latitude,  origin.longitude,
            airport.latitude, airport.longitude,
        )
        if dist <= radius_km:
            nearby.append((dist, airport))

    if not nearby:
        return []

    # Sort by type (large first) then distance
    type_rank = {"large_airport": 0, "medium_airport": 1}

    nearby.sort(key=lambda x: (
        type_rank.get(x[1].airport_type, 2),
        x[0]
    ))

    result = [airport for _, airport in nearby[:max_results]]

    log.debug(
        "Found %d nearby airports within %dkm of %s: %s",
        len(result), radius_km, iata_code,
        [a.iata_code for a in result]
    )

    return result


def get_sample_dates(target_date, flex_days, is_nearby=False):
    """
    Generate sample departure dates for price checking.
    Entered airports: up to 9 sample points
    Nearby airports:  every other point (half sample)

    target_date: datetime.date object
    flex_days:   number of days either side to check (0 = fixed)
    is_nearby:   if True, use half the sample points
    """
    from datetime import timedelta

    if flex_days == 0:
        return [target_date]

    total_days = flex_days * 2
    step       = max(1, total_days // 8)  # ~9 points for entered airports

    dates = set()
    current = target_date - timedelta(days=flex_days)
    end     = target_date + timedelta(days=flex_days)

    while current <= end:
        dates.add(current)
        current += timedelta(days=step)

    dates.add(target_date)  # Always include target

    sorted_dates = sorted(dates)

    if is_nearby:
        # Half sample — every other date, always keep target
        half = [d for i, d in enumerate(sorted_dates) if i % 2 == 0]
        if target_date not in half:
            half.append(target_date)
        return sorted(half)

    return sorted_dates
