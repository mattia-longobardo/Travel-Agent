from math import radians, sin, cos, asin, sqrt

# IATA, città, paese, lat, lon — principali hub (estendibile)
AIRPORTS = [
    ("MXP", "Milano", "IT", 45.63, 8.72), ("LIN", "Milano", "IT", 45.45, 9.28),
    ("BGY", "Bergamo", "IT", 45.67, 9.70), ("FCO", "Roma", "IT", 41.80, 12.25),
    ("CIA", "Roma", "IT", 41.80, 12.59), ("NAP", "Napoli", "IT", 40.88, 14.29),
    ("VCE", "Venezia", "IT", 45.50, 12.35), ("BLQ", "Bologna", "IT", 44.53, 11.30),
    ("CTA", "Catania", "IT", 37.47, 15.07), ("PMO", "Palermo", "IT", 38.18, 13.10),
    ("TRN", "Torino", "IT", 45.20, 7.65), ("PSA", "Pisa", "IT", 43.68, 10.39),
    ("BRI", "Bari", "IT", 41.14, 16.76), ("CAG", "Cagliari", "IT", 39.25, 9.05),
    ("NCE", "Nizza", "FR", 43.66, 7.21), ("CDG", "Parigi", "FR", 49.01, 2.55),
    ("ORY", "Parigi", "FR", 48.72, 2.38), ("LYS", "Lione", "FR", 45.73, 5.08),
    ("MRS", "Marsiglia", "FR", 43.44, 5.22), ("BCN", "Barcellona", "ES", 41.30, 2.08),
    ("MAD", "Madrid", "ES", 40.47, 3.56), ("AGP", "Malaga", "ES", 36.67, 4.50),
    ("PMI", "Palma", "ES", 39.55, 2.74), ("VLC", "Valencia", "ES", 39.49, 0.48),
    ("LIS", "Lisbona", "PT", 38.77, 9.13), ("OPO", "Porto", "PT", 41.24, 8.68),
    ("FNC", "Funchal", "PT", 32.69, 16.78), ("PDL", "Ponta Delgada", "PT", 37.74, 25.70),
    ("TFS", "Tenerife", "ES", 28.04, 16.57), ("LPA", "Gran Canaria", "ES", 27.93, 15.39),
    ("ACE", "Lanzarote", "ES", 28.95, 13.61), ("FUE", "Fuerteventura", "ES", 28.45, 13.86),
    ("LHR", "Londra", "GB", 51.47, 0.45), ("LGW", "Londra", "GB", 51.15, 0.18),
    ("AMS", "Amsterdam", "NL", 52.31, 4.76), ("BRU", "Bruxelles", "BE", 50.90, 4.48),
    ("FRA", "Francoforte", "DE", 50.03, 8.57), ("MUC", "Monaco", "DE", 48.35, 11.79),
    ("ZRH", "Zurigo", "CH", 47.46, 8.55), ("GVA", "Ginevra", "CH", 46.24, 6.11),
    ("VIE", "Vienna", "AT", 48.11, 16.57), ("ATH", "Atene", "GR", 37.94, 23.95),
    ("HER", "Heraklion", "GR", 35.34, 25.18), ("JTR", "Santorini", "GR", 36.40, 25.48),
]

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * r * asin(sqrt(a))

def nearest_airports(lat: float, lon: float, k: int = 3) -> list[dict]:
    scored = [
        {"iata": i, "city": c, "country": co, "km": round(haversine_km(lat, lon, la, lo), 1)}
        for (i, c, co, la, lo) in AIRPORTS
    ]
    scored.sort(key=lambda x: x["km"])
    return scored[:k]


def airports_within(lat: float, lon: float, radius_km: float = 80.0,
                    max_n: int = 4) -> list[dict]:
    """All airports within ``radius_km`` of (lat, lon), sorted by distance and capped at
    ``max_n``. Never empty: if none fall inside the radius, returns the single nearest one."""
    scored = [
        {"iata": i, "city": c, "country": co, "km": round(haversine_km(lat, lon, la, lo), 1)}
        for (i, c, co, la, lo) in AIRPORTS
    ]
    scored.sort(key=lambda x: x["km"])
    within = [a for a in scored if a["km"] <= radius_km]
    if not within:
        return nearest_airports(lat, lon, 1)
    return within[:max_n]
