"""Read-only property presentation data, deliberately separated from checkout links."""

import asyncio
import hashlib
import json
import math
import os
import re
import time
import unicodedata
from collections.abc import Mapping
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, Query

from app.agent.tool_perimeters import NS
from app.deps import get_current_user, get_mcp
from app.models import User
from app.property_urls import resolve_public_property_url
from app.redis_client import get_redis

router = APIRouter(prefix="/api/properties", tags=["properties"])

_MARKDOWN_LINK = re.compile(r"\[[^]]*]\((https?://[^)]+)\)")
_NOMINATIM_URL = os.getenv("TRAVEL_NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
_NOMINATIM_USER_AGENT = os.getenv(
    "TRAVEL_NOMINATIM_USER_AGENT",
    "TravelAgent/1.0 (https://travel.longobardo.me)",
)
_GEOCODE_SPACING_SECONDS = 1.05
_GEOCODE_TTL = 60 * 60 * 24 * 30
_GEOCODE_NEGATIVE_TTL = 60 * 60 * 24
_GEOCODE_LOCK = asyncio.Lock()
_last_geocode_at = 0.0
_GENERIC_PLACE_TYPES = {"administrative", "city", "county", "municipality", "state", "town", "village"}
_ADDRESS_WORDS = {
    "avenue", "boulevard", "calle", "carrer", "corso", "lane", "piazza", "place", "platz",
    "plaza", "road", "rue", "strada", "street", "via", "viale", "weg",
}
_SQUARE_WORDS = {"piazza", "place", "platz", "plaza"}
_ADDRESS_STOPWORDS = _ADDRESS_WORDS | {
    "dei", "del", "della", "delle", "di", "the", "and", "und", "des", "le", "la",
}


def _safe_http(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    return url if parsed.scheme in {"http", "https"} and parsed.netloc else None


def _gallery_urls(values) -> list[str]:
    out: list[str] = []
    for value in values if isinstance(values, list) else []:
        if not isinstance(value, str):
            continue
        match = _MARKDOWN_LINK.search(value)
        candidate = match.group(1) if match else value
        safe = _safe_http(candidate)
        if safe and safe not in out:
            out.append(safe)
    return out[:12]


def _string_list(values) -> list[str]:
    if isinstance(values, str):
        values = [values]
    out: list[str] = []
    for value in values if isinstance(values, list) else []:
        if isinstance(value, str) and value.strip() and value.strip() not in out:
            out.append(value.strip())
    return out


def _public_policies(values) -> dict:
    """Expose public policy values while dropping nested/internal provider objects."""
    if not isinstance(values, Mapping):
        return {}
    out = {}
    for key, value in values.items():
        if not isinstance(key, str):
            continue
        if value is None or isinstance(value, (str, bool, int, float)):
            out[key] = value
        elif isinstance(value, list):
            out[key] = [item for item in value if isinstance(item, (str, bool, int, float))]
    return out


def _float(value) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _valid_coordinates(lat, lng) -> tuple[float, float] | None:
    lat_value, lng_value = _float(lat), _float(lng)
    if lat_value is None or lng_value is None:
        return None
    if not (-90 <= lat_value <= 90 and -180 <= lng_value <= 180):
        return None
    if lat_value == 0 and lng_value == 0:
        return None
    return lat_value, lng_value


def _coordinates_from(value) -> tuple[float, float] | None:
    if isinstance(value, Mapping):
        for lat_key, lng_key in (
            ("latitude", "longitude"), ("lat", "lng"), ("lat", "lon"),
        ):
            pair = _valid_coordinates(value.get(lat_key), value.get(lng_key))
            if pair:
                return pair
        coordinates = value.get("coordinates")
        if isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
            # GeoJSON order is longitude, latitude.
            pair = _valid_coordinates(coordinates[1], coordinates[0])
            if pair:
                return pair
        for key in ("location", "geo", "position"):
            pair = _coordinates_from(value.get(key))
            if pair:
                return pair
    return None


def _provider_location(hotel: dict, data: dict) -> dict | None:
    pair = _coordinates_from(hotel)
    if not pair:
        for key in ("location", "geo", "position"):
            pair = _coordinates_from(data.get(key))
            if pair:
                break
    if not pair:
        return None
    return {
        "lat": pair[0],
        "lng": pair[1],
        "label": hotel.get("address") or hotel.get("name") or "Struttura",
        "source": "provider",
        "confidence": 1.0,
    }


def _plain(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch)).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


def _specific_address(address: str, destination: str) -> bool:
    address_plain, destination_plain = _plain(address), _plain(destination)
    if not address_plain or not destination_plain or address_plain == destination_plain:
        return False
    parts = address_plain.split()
    return len(parts) >= 2 and (
        any(ch.isdigit() for ch in address_plain)
        or any(part in _ADDRESS_WORDS for part in parts)
    )


def _street_segment(result: dict) -> tuple[str, str]:
    """Return the result's street text and house-number source, preferring addressdetails."""
    details = result.get("address") if isinstance(result.get("address"), Mapping) else {}
    for key in ("road", "pedestrian", "residential", "footway", "path", "square", "place"):
        value = details.get(key)
        if isinstance(value, str) and value.strip():
            number = details.get("house_number")
            return value.strip(), str(number or "")
    segments = [part.strip() for part in str(result.get("display_name") or "").split(",") if part.strip()]
    if not segments:
        return "", ""
    # Nominatim sometimes formats a property as "10, Via Roma, Milano".
    if re.fullmatch(r"\d+[a-zA-Z/-]*", segments[0]) and len(segments) > 1:
        return segments[1], segments[0]
    return segments[0], segments[0]


def _street_terms(value: str) -> set[str]:
    return {
        term for term in _plain(value).split()
        if len(term) > 2 and not term.isdigit() and term not in _ADDRESS_STOPWORDS
    }


def _street_kind(value: str) -> str | None:
    terms = set(_plain(value).split())
    if terms.intersection(_SQUARE_WORDS):
        return "square"
    if terms.intersection(_ADDRESS_WORDS):
        return "road"
    return None


def _house_numbers(value: str) -> set[str]:
    # Compare the numeric part so "10" and "10/A" remain coherent.
    return set(re.findall(r"\d+", _plain(value)))


def _confident_geocode(
    result: dict,
    address: str,
    destination: str,
    *,
    require_destination: bool = True,
) -> bool:
    if not isinstance(result, dict) or result.get("type") in _GENERIC_PLACE_TYPES:
        return False
    if result.get("category") == "boundary" or result.get("class") == "boundary":
        return False
    if not _valid_coordinates(result.get("lat"), result.get("lon")):
        return False
    display = _plain(result.get("display_name"))
    destination_clean = _plain(re.sub(r"\([^)]*\)", " ", destination))
    destination_terms = [term for term in destination_clean.split() if len(term) > 2]
    if require_destination and destination_terms and not any(term in display for term in destination_terms):
        return False
    query_street = address.split(",", 1)[0].strip()
    result_street, result_number_source = _street_segment(result)
    query_terms = _street_terms(query_street)
    result_terms = _street_terms(result_street)
    # A city or house-number match alone is never sufficient: the street itself must match.
    if not query_terms or not query_terms.issubset(result_terms):
        return False
    query_kind, result_kind = _street_kind(query_street), _street_kind(result_street)
    if query_kind and result_kind and query_kind != result_kind:
        return False
    # Provider addresses commonly put the civic number after the first comma
    # ("Estrada do Garajau, 131"). Inspect the street plus its next segment, but not later
    # city/postcode components.
    query_address_head = ",".join(address.split(",")[:2])
    query_number_parts = re.findall(r"\d+", _plain(query_address_head))
    # In a street-address query the final numeric component is the civic number; earlier
    # numbers may legitimately belong to the street name (for example "Via 20 Settembre 5").
    query_numbers = {query_number_parts[-1]} if query_number_parts else set()
    if query_numbers:
        result_numbers = _house_numbers(result_number_source)
        if not result_numbers or query_numbers.isdisjoint(result_numbers):
            return False
    return True


def _geocode_cache_key(address: str, destination: str, name: str = "") -> str:
    digest = hashlib.sha256(
        f"{_plain(address)}|{_plain(destination)}|{_plain(name)}".encode()
    ).hexdigest()
    return f"property-geocode:v2:{digest}"


async def _cached_geocode(key: str) -> tuple[bool, dict | None]:
    try:
        raw = await get_redis().get(key)
    except Exception:
        return False, None
    if raw is None:
        return False, None
    if isinstance(raw, bytes):
        raw = raw.decode()
    if raw == "null":
        return True, None
    try:
        value = json.loads(raw)
    except Exception:
        return False, None
    return (True, value) if isinstance(value, dict) else (False, None)


async def _cache_geocode(key: str, location: dict | None) -> None:
    try:
        await get_redis().set(
            key,
            json.dumps(location, separators=(",", ":")) if location else "null",
            ex=_GEOCODE_TTL if location else _GEOCODE_NEGATIVE_TTL,
        )
    except Exception:
        pass


async def _geocode_property(
    address: str | None,
    destination: str | None,
    name: str | None = None,
) -> dict | None:
    """Geocode a specific street address conservatively; never place a city-only marker."""
    if not isinstance(address, str) or not isinstance(destination, str):
        return None
    address, destination = address.strip(), destination.strip()
    property_name = name.strip() if isinstance(name, str) else ""
    if not _specific_address(address, property_name or destination):
        return None
    key = _geocode_cache_key(address, destination, property_name)
    found, cached = await _cached_geocode(key)
    if found:
        return cached

    global _last_geocode_at
    async with _GEOCODE_LOCK:
        # A second request may have populated the cache while this request waited for the lock.
        found, cached = await _cached_geocode(key)
        if found:
            return cached
        wait_for = _GEOCODE_SPACING_SECONDS - (time.monotonic() - _last_geocode_at)
        if wait_for > 0:
            await asyncio.sleep(wait_for)
        _last_geocode_at = time.monotonic()
        location = None
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(3.0),
                follow_redirects=False,
                headers={"User-Agent": _NOMINATIM_USER_AGENT, "Accept-Language": "it,en;q=0.8"},
            ) as client:
                query = f"{property_name}, {address}" if property_name else f"{address}, {destination}"
                response = await client.get(_NOMINATIM_URL, params={
                    "q": query,
                    "format": "jsonv2",
                    "limit": 1,
                    "addressdetails": 1,
                })
                response.raise_for_status()
                payload = response.json()
            result = payload[0] if isinstance(payload, list) and payload else None
            if isinstance(result, dict) and _confident_geocode(
                result,
                address,
                destination,
                # Airport/city search destinations can be broader than the hotel's actual
                # municipality. A name+street+civic query is validated by the exact address
                # instead of requiring that broad destination text in the result.
                require_destination=not property_name,
            ):
                pair = _valid_coordinates(result.get("lat"), result.get("lon"))
                if pair:
                    location = {
                        "lat": pair[0],
                        "lng": pair[1],
                        "label": result.get("display_name") or f"{address}, {destination}",
                        "source": "nominatim",
                        "confidence": 0.8,
                    }
        except Exception:
            location = None
        await _cache_geocode(key, location)
        return location


async def _resolve_original_url(hotel_id: int) -> str | None:
    """Keep the optional public-page enrichment from breaking property presentation."""
    try:
        return await resolve_public_property_url(hotel_id)
    except Exception:
        return None


def _partial_property_details(hotel_id: int, original_url: str | None) -> dict:
    """Stable response used when the provider search session no longer has full details."""
    return {
        "id": hotel_id,
        "name": None,
        "address": None,
        "stars": None,
        "check_in_time": None,
        "check_out_time": None,
        "description": None,
        "gallery": [],
        "facilities": [],
        "policies": {},
        "original_url": original_url,
        "location": None,
        "total_room_options": 0,
        "rooms": [],
        "details_status": "partial",
        "partial": True,
    }


@router.get("/{hotel_id}")
async def property_details(
    hotel_id: int,
    search_id: int = Query(..., gt=0),
    date_from: str = Query(...),
    date_to: str = Query(...),
    destination: str = "",
    user: User = Depends(get_current_user),
    mcp=Depends(get_mcp),
):
    del user  # Access control is the only use of the injected user.
    # Resolve the public presentation URL independently from the short-lived provider search
    # session. Even when room selection has expired, the client can still render its cached card
    # data and offer the verified original property page.
    original_url_task = asyncio.create_task(_resolve_original_url(hotel_id))
    try:
        raw = await mcp.call_tool(NS + "select_hotel_options", {
            "search_id": search_id,
            "hotel_internal_id": hotel_id,
            "date_from": date_from,
            "date_to": date_to,
        })
        data = json.loads(raw)
        if isinstance(data, list) and data:
            data = data[0]
    except Exception:
        return _partial_property_details(hotel_id, await original_url_task)
    if (
        not isinstance(data, dict)
        or data.get("success") is False
        or not isinstance(data.get("hotel"), dict)
    ):
        return _partial_property_details(hotel_id, await original_url_task)

    hotel = data.get("hotel") if isinstance(data.get("hotel"), dict) else {}
    policies = data.get("policies") if isinstance(data.get("policies"), dict) else {}
    rooms = data.get("room_options") if isinstance(data.get("room_options"), list) else []
    facilities = _string_list(
        hotel.get("facilities") or hotel.get("amenities")
        or data.get("facilities") or data.get("amenities") or []
    )
    location = _provider_location(hotel, data)
    if location is None:
        location, original_url = await asyncio.gather(
            _geocode_property(hotel.get("address"), destination, hotel.get("name")),
            original_url_task,
        )
    else:
        original_url = await original_url_task
    # No pricing/rate/pricing IDs are exposed here: this endpoint backs a presentation page,
    # never a booking action.
    return {
        "id": hotel.get("id") or hotel_id,
        "name": hotel.get("name"),
        "address": hotel.get("address"),
        "stars": hotel.get("stars"),
        "check_in_time": hotel.get("check_in_time"),
        "check_out_time": hotel.get("check_out_time"),
        "description": hotel.get("description"),
        "gallery": _gallery_urls(hotel.get("gallery_links") or hotel.get("gallery") or []),
        "facilities": facilities,
        "policies": _public_policies(policies),
        "original_url": original_url,
        "location": location,
        "total_room_options": data.get("total_room_options") or len(rooms),
        "rooms": [
            {
                "name": room.get("room_name"),
                "meal_plan": room.get("meal_plan"),
                "cancellation": room.get("cancellation"),
                "deposit_required": room.get("deposit_required"),
                "price": room.get("price"),
                "currency": room.get("currency"),
                "price_note": room.get("price_note"),
            }
            for room in rooms if isinstance(room, dict)
        ],
        "details_status": "complete",
        "partial": False,
    }
