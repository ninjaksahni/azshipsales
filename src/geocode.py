from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from src.city_coords import CITY_COORDINATES, normalize_city_name

CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "geocode_cache.json"
USER_AGENT = "azshipsales/1.0 (fulfillment map; contact: local)"
OPEN_METEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def _cache_key(city: str) -> str:
    return normalize_city_name(city)


def load_geocode_cache() -> dict[str, Any]:
    if not CACHE_PATH.exists():
        return {}
    with CACHE_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def save_geocode_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _static_coords(city: str) -> tuple[float, float] | None:
    key = _cache_key(city)
    if key in CITY_COORDINATES:
        return CITY_COORDINATES[key]
    upper = city.strip().upper()
    if upper in CITY_COORDINATES:
        return CITY_COORDINATES[upper]
    return None


def _open_meteo_search(query: str) -> tuple[float, float] | None:
    params = urllib.parse.urlencode(
        {
            "name": query,
            "count": 10,
            "language": "en",
            "format": "json",
            "countryCode": "IN",
        }
    )
    url = f"{OPEN_METEO_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())

    results = data.get("results") or []
    india = [r for r in results if r.get("country_code") == "IN"]
    if not india and results:
        india = results
    if not india:
        return None

    best = max(india, key=lambda r: int(r.get("population") or 0))
    return float(best["latitude"]), float(best["longitude"])


def _nominatim_search(query: str) -> tuple[float, float] | None:
    params = urllib.parse.urlencode(
        {
            "q": query,
            "format": "json",
            "limit": 1,
            "countrycodes": "in",
        }
    )
    url = f"{NOMINATIM_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    time.sleep(1.05)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])


def _build_queries(city: str, state: str) -> list[str]:
    city = re.sub(r"\s+", " ", city.strip())
    state = state.strip()
    queries = []
    if state:
        queries.append(f"{city}, {state}, India")
    queries.append(f"{city}, India")
    queries.append(city)
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out


def fetch_city_coordinates(city: str, state: str = "") -> tuple[float, float] | None:
    static = _static_coords(city)
    if static:
        return static

    for query in _build_queries(city, state):
        try:
            coords = _open_meteo_search(query)
            if coords:
                time.sleep(0.12)
                return coords
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
            pass

    for query in _build_queries(city, state):
        try:
            coords = _nominatim_search(query)
            if coords:
                return coords
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
            pass

    return None


def get_city_coordinates(
    city: str,
    state: str = "",
    *,
    allow_fetch: bool = True,
    cache: dict[str, Any] | None = None,
) -> tuple[float, float] | None:
    key = _cache_key(city)
    if not key:
        return None

    static = _static_coords(city)
    if static:
        return static

    if cache is None:
        cache = load_geocode_cache()

    hit = cache.get(key)
    if isinstance(hit, dict):
        if hit.get("failed"):
            return None
        if "lat" in hit and "lon" in hit:
            return float(hit["lat"]), float(hit["lon"])

    if not allow_fetch:
        return None

    coords = fetch_city_coordinates(city, state)
    if coords:
        cache[key] = {
            "lat": coords[0],
            "lon": coords[1],
            "source": "api",
            "city": city,
            "state": state,
        }
        save_geocode_cache(cache)
    else:
        cache[key] = {
            "failed": True,
            "city": city,
            "state": state,
        }
        save_geocode_cache(cache)
    return coords


def city_geocode_pending(city: str, cache: dict[str, Any] | None = None) -> bool:
    """True if this city still needs a one-time geocode attempt."""
    key = _cache_key(city)
    if not key or _static_coords(city):
        return False
    if cache is None:
        cache = load_geocode_cache()
    hit = cache.get(key)
    if isinstance(hit, dict):
        if hit.get("failed"):
            return False
        if "lat" in hit and "lon" in hit:
            return False
    return True


def collect_city_states(skus: dict[str, Any]) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for data in skus.values():
        for city, bucket in data.get("cities", {}).items():
            state = str(bucket.get("state") or pairs.get(city, "")).strip()
            pairs[city] = state
    return pairs


def ensure_coordinates_for_cities(
    city_states: dict[str, str],
    *,
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, int]:
    cache = load_geocode_cache()
    missing = [c for c in city_states if city_geocode_pending(c, cache)]
    resolved = 0
    failed = 0
    total = len(missing)

    for i, city in enumerate(missing, start=1):
        if progress:
            progress(i, total)
        before = len(cache)
        coords = get_city_coordinates(
            city, city_states[city], allow_fetch=True, cache=cache
        )
        if coords:
            resolved += 1
        else:
            failed += 1
        if len(cache) > before:
            save_geocode_cache(cache)

    return {"resolved": resolved, "failed": failed, "already": len(city_states) - total}


def lookup_coordinates(city: str, state: str = "") -> tuple[float, float] | None:
    return get_city_coordinates(city, state, allow_fetch=False)
