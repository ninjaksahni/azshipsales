from __future__ import annotations

import re
from typing import Tuple

# Lat/lon for Indian cities (normalized uppercase keys).
CITY_COORDINATES: dict[str, tuple[float, float]] = {
    "AGARTALA": (23.8315, 91.2868),
    "AHMADNAGAR": (19.0952, 74.7496),
    "AHMEDABAD": (23.0225, 72.5714),
    "AIZAWL": (23.7271, 92.7176),
    "ARIYUR": (12.0989, 79.0786),
    "BALESHWAR": (21.4942, 86.9320),
    "BASTI": (26.7945, 82.7644),
    "BENGALURU": (12.9716, 77.5946),
    "BHUBANESWAR": (20.2961, 85.8245),
    "BIHARSHARIF": (25.1982, 85.5234),
    "BORHOLLA": (27.1800, 94.8200),
    "CHANDIGARH": (30.7333, 76.7794),
    "CHENNAI": (13.0827, 80.2707),
    "CHEYYUR": (12.6594, 79.8497),
    "CHITTOOR": (13.2171, 79.1003),
    "COIMBATORE": (11.0168, 76.9558),
    "DANDELI": (15.2667, 74.6167),
    "DEHRADUN": (30.3165, 78.0322),
    "DHARMAPURI": (12.1274, 78.1579),
    "DIMAPUR": (25.9043, 93.7266),
    "ERNAKULAM": (9.9816, 76.2999),
    "GHAZIABAD": (28.6692, 77.4538),
    "GREATER NOIDA": (28.4744, 77.5040),
    "GURUGRAM": (28.4595, 77.0266),
    "GUWAHATI": (26.1445, 91.7362),
    "HAJIPUR": (25.6854, 85.2086),
    "HAZARIBAGH": (23.9966, 85.3691),
    "HIRIYUR": (13.9477, 76.6141),
    "HYDERABAD": (17.3850, 78.4867),
    "INDORE": (22.7196, 75.8577),
    "IROOPARA": (8.5089, 76.9969),
    "JAIPUR": (26.9124, 75.7873),
    "JHUMRI TILAIYA": (24.1319, 86.1477),
    "KALYAN": (19.2403, 73.1305),
    "KANGRA": (32.0998, 76.2691),
    "KANKE": (23.3088, 85.3213),
    "KOLKATA": (22.5726, 88.3639),
    "KOTHAMANGALAM": (10.0619, 76.6297),
    "KOTTAYAM": (9.5916, 76.5222),
    "KUNNATHUNAD": (10.1500, 76.2000),
    "LABBAIKUDIKADU": (10.9000, 78.7000),
    "LAMBHVEL": (22.8000, 72.7000),
    "MANGALURU": (12.9141, 74.8560),
    "MARGAO": (15.2832, 73.9862),
    "MOHALI": (30.7046, 76.7179),
    "MUMBAI": (19.0760, 72.8777),
    "MUZAFFARPUR": (26.1209, 85.3647),
    "NAGPUR": (21.1458, 79.0882),
    "NAVI MUMBAI": (19.0330, 73.0297),
    "NEW DELHI": (28.6139, 77.2090),
    "NEW TOWN": (22.5833, 88.4667),
    "NOIDA": (28.5355, 77.3910),
    "PANCHKULA": (30.6942, 76.8606),
    "PATIALA": (30.3398, 76.3869),
    "PIMPRI CHINCHWAD": (18.6298, 73.7997),
    "PONDICHERRY": (11.9416, 79.8083),
    "PUDUCHERRY": (11.9416, 79.8083),
    "PUNE": (18.5204, 73.8567),
    "RAMPUR BUSHAHR": (31.4522, 77.7820),
    "RANCHI": (23.3441, 85.3096),
    "RUSHIKONDA APIIC": (17.7892, 83.3573),
    "SAMBA": (32.5713, 75.1089),
    "SAO JOSE DE AREAL": (15.4000, 73.9000),
    "SECUNDERABAD": (17.4399, 78.4983),
    "SHILLONGS": (25.5788, 91.8933),
    "SURAT": (21.1702, 72.8311),
    "THANE": (19.2183, 72.9781),
    "THANE WEST": (19.2100, 72.9600),
    "TIPTUR": (13.2563, 76.4777),
    "TIRUVANNAMALAI": (12.2253, 79.0747),
    "UMRETH": (22.7000, 73.1000),
    "UNDARAJAVARAM": (16.8000, 81.7000),
    "VADODARA": (22.3072, 73.1812),
    "VISAKHAPATNAM": (17.6868, 83.2185),
    "VUYYURU": (16.3600, 80.9300),
    "YAMUNANAGAR": (30.1290, 77.2674),
    "YAVATMAL": (20.3888, 78.1204),
    "ZIKZAK": (25.5000, 91.8000),
}

_ALIASES: dict[str, str] = {
    "HAJIPUR. , VAISHALI": "HAJIPUR",
    "BANGALORE": "BENGALURU",
    "GURGAON": "GURUGRAM",
    "DELHI": "NEW DELHI",
}


def normalize_city_name(city: str) -> str:
    name = city.strip().upper()
    name = re.sub(r"\s+", " ", name)
    name = _ALIASES.get(name, name)
    if name in CITY_COORDINATES:
        return name
    # Strip punctuation clutter
    cleaned = re.sub(r"[^A-Z0-9 ]", "", name).strip()
    cleaned = _ALIASES.get(cleaned, cleaned)
    return cleaned


def city_coordinates(city: str) -> Tuple[float, float] | None:
    key = normalize_city_name(city)
    if key in CITY_COORDINATES:
        return CITY_COORDINATES[key]
    if city.strip().upper() in CITY_COORDINATES:
        return CITY_COORDINATES[city.strip().upper()]
    return None
