import asyncio
import json
import re
from datetime import datetime
from collections.abc import Mapping
from app.agent.accommodation import ACCOMMODATION_FILTERS, requested_accommodation_kinds
from app.agent.currency import EUR, is_eur_offer
from app.agent.media import first_image
from app.agent.identity import extract_destination_code, extract_hotel_id, extract_search_id
from app.agent.price import parse_price
from app.agent.search import CONCURRENCY, bounded_call
from app.agent.slots import slots_for_state
from app.agent.tool_perimeters import NS

SEARCH = NS + "search_flight_and_hotel_package"

_TIME = re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b")
_IATA = re.compile(r"\b[A-Z]{3}\b")
_ARROW = re.compile(r"→|->")
_SEGMENT_BREAK = re.compile(r"[|·;\n]")
_DURATION_WORD = re.compile(r"\b(?:durata|duration|durée|dauer)\b", re.I)
_DEPARTURE_WORD = re.compile(r"\b(?:partenza|departure|departing|decollo)\b", re.I)
_ARRIVAL_WORD = re.compile(r"\b(?:arrivo|arrival|arriving|atterraggio)\b", re.I)


def _segment_before(value: str, position: int) -> str:
    prefix = value[:position]
    breaks = list(_SEGMENT_BREAK.finditer(prefix))
    return prefix[breaks[-1].end():] if breaks else prefix


def _segment_after(value: str, position: int) -> str:
    suffix = value[position:]
    boundary = _SEGMENT_BREAK.search(suffix)
    return suffix[:boundary.start()] if boundary else suffix


def _time_is_duration(segment: str, match: re.Match) -> bool:
    return bool(_DURATION_WORD.search(segment[max(0, match.start() - 18):match.start()]))


def flight_summary_has_times(value: str | None) -> bool:
    """Return true only for a real leg with a departure time and an arrival time.

    Counting timestamps is unsafe: a departure plus a duration, or two departure times, would
    suppress the exact-package enrichment. Accept an explicit route arrow with a non-duration
    time on each side, or unambiguous departure/arrival wording.
    """
    if not isinstance(value, str) or not value.strip():
        return False
    for arrow in _ARROW.finditer(value):
        left = _segment_before(value, arrow.start())
        right = _segment_after(value, arrow.end())
        left_times = list(_TIME.finditer(left))
        right_time = _TIME.search(right)
        if not left_times or right_time is None:
            continue
        left_time = left_times[-1]
        if _time_is_duration(left, left_time) or _time_is_duration(right, right_time):
            continue
        left_prefix = left[max(0, left_time.start() - 28):left_time.start()]
        right_prefix = right[max(0, right_time.start() - 28):right_time.start()]
        # An arrow between two values both labelled as departures/arrivals is not a leg.
        if _ARRIVAL_WORD.search(left_prefix) and not _DEPARTURE_WORD.search(left_prefix):
            continue
        if _DEPARTURE_WORD.search(right_prefix) and not _ARRIVAL_WORD.search(right_prefix):
            continue
        # A bare time range is ambiguous (it may be a duration or opening interval). Require
        # actual route endpoints, or explicit departure/arrival semantics.
        has_route_endpoints = bool(_IATA.search(left) and _IATA.search(right))
        has_endpoint_words = bool(_DEPARTURE_WORD.search(left) and _ARRIVAL_WORD.search(right))
        if not (has_route_endpoints or has_endpoint_words):
            continue
        return True

    # Some providers spell the endpoints out instead of using an arrow.
    departure = _DEPARTURE_WORD.search(value)
    if departure:
        departure_time = _TIME.search(value, departure.end())
        arrival = _ARRIVAL_WORD.search(value, departure_time.end() if departure_time else departure.end())
        arrival_time = _TIME.search(value, arrival.end()) if arrival else None
        if departure_time and arrival and arrival_time:
            return not (_time_is_duration(value, departure_time) or _time_is_duration(value, arrival_time))
    return False


def _date_time(value) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value.strip()
    return parsed.strftime("%d/%m %H:%M")


def _leg_summary(value, label: str) -> str | None:
    if isinstance(value, str) and value.strip():
        return f"{label}: {value.strip()}"
    if not isinstance(value, Mapping):
        return None
    origin = value.get("from") or value.get("origin") or value.get("departure_airport")
    destination = value.get("to") or value.get("destination") or value.get("arrival_airport")
    departure = _date_time(value.get("departure_time") or value.get("departure"))
    arrival = _date_time(value.get("arrival_time") or value.get("arrival"))
    # A structured leg is complete only when both endpoints have a time. Otherwise an
    # outbound departure plus an inbound arrival could misleadingly look like one complete leg.
    if not (departure and arrival):
        return None
    departure_text = " ".join(str(part) for part in (origin, departure) if part)
    arrival_text = " ".join(str(part) for part in (destination, arrival) if part)
    return f"{label}: {departure_text} → {arrival_text}".strip()


def flight_details_summary(value) -> str | None:
    """Format only flight legs actually returned for this exact package selection."""
    if not isinstance(value, Mapping):
        return None
    outbound = _leg_summary(value.get("outbound") or value.get("outward"), "A")
    inbound = _leg_summary(value.get("inbound") or value.get("return"), "R")
    parts = [part for part in (outbound, inbound) if part]
    return " · ".join(parts) if parts else None


def package_flight_summary(item: dict) -> tuple[str, str | None]:
    """Return (display summary, carrier), never a bare carrier name."""
    hotel_flight = item.get("flight") if isinstance(item.get("flight"), Mapping) else {}
    carrier = item.get("carrier") or hotel_flight.get("carrier") or hotel_flight.get("airline")
    explicit = item.get("flight_summary") or item.get("summary") or hotel_flight.get("summary")
    if isinstance(explicit, str) and flight_summary_has_times(explicit):
        return explicit.strip(), str(carrier) if carrier else None
    for details in (item.get("flight_details"), hotel_flight.get("flight_details"), item, hotel_flight):
        summary = flight_details_summary(details)
        if summary and flight_summary_has_times(summary):
            return summary, str(carrier) if carrier else None
    if carrier:
        return f"Orari non disponibili · Compagnia {carrier}", str(carrier)
    if isinstance(explicit, str) and explicit.strip():
        return f"Orari non disponibili · {explicit.strip()}", None
    return "Orari del volo non disponibili", None


def _parse(raw: str) -> tuple[object, list[dict]]:
    """Return (top-level object, product items). The top-level ``search_id`` + each item's
    ``internal_id_hotel`` let the presenter mint a real booking link via
    select_hotel_options -> generate_booking_link."""
    try:
        data = json.loads(raw)
    except Exception:
        return None, []
    if isinstance(data, dict):
        items = data.get("products_summary") or data.get("results") or data.get("packages") or []
        return data, (items if isinstance(items, list) else [])
    return data, (data if isinstance(data, list) else [])


def _items(raw: str) -> list[dict]:
    return _parse(raw)[1]


def normalize_packages(raw: str, adults: int = 1,
                       accommodation_kind: str = "hotel") -> list[dict]:
    """lastminute returns the package price as the TOTAL for the party; divide by adults."""
    adults = max(adults or 1, 1)
    data, items = _parse(raw)
    out = []
    for it in items:
        if not is_eur_offer(it, data):
            continue
        total = parse_price(it.get("price_total"))
        if total is None:
            total = parse_price(it.get("total_price"))
        if total is None and it.get("total_price_cents") is not None:
            cents = parse_price(it["total_price_cents"])
            total = cents / 100 if cents is not None else None
        hotel = it.get("hotel") or {}
        flight = it.get("flight") or {}
        facilities = it.get("facilities")
        if not isinstance(facilities, list):
            facilities = hotel.get("facilities") or hotel.get("amenities") or []
        cancellable = it.get("cancellable")
        if cancellable is None:
            cancellable = hotel.get("cancellable")
        flight_summary, flight_carrier = package_flight_summary(it)
        out.append({
            "price_total": round(total, 2) if total is not None else None,
            "price_per_person": round(total / adults, 2) if total is not None else None,
            "currency": EUR,
            "hotel_name": it.get("name") or hotel.get("name"),
            "hotel_stars": it.get("stars") or hotel.get("stars"),
            "hotel_rating": it.get("rating") or hotel.get("rating"),
            "hotel_reviews": it.get("reviews") if it.get("reviews") is not None else hotel.get("reviews"),
            "hotel_distance_km": (it.get("distance_km") if it.get("distance_km") is not None
                                  else hotel.get("distance_km")),
            "hotel_facilities": [value.strip() for value in facilities
                                 if isinstance(value, str) and value.strip()],
            "hotel_cancellable": cancellable,
            "flight_summary": flight_summary,
            "flight_carrier": flight_carrier,
            "image_url": first_image(it),
            "search_id": extract_search_id(data, it),
            "lm_dest_code": extract_destination_code(data, it),
            "hotel_internal_id": extract_hotel_id(it),
            "accommodation_kind": accommodation_kind,
            "pricing_id": it.get("pricing_id"),
            "rate_id": it.get("rate_id"),
        })
    return [p for p in out if p["price_per_person"] is not None]


async def package_node(state, llm=None, mcp=None) -> dict:
    packages: dict[str, list[dict]] = {}
    if mcp is None:
        return {"packages": packages}
    origin = (state.get("origin_iata") or ["MXP"])[0]
    adults = state.get("adults", 1) or 1
    slots = slots_for_state(state)
    sem = asyncio.Semaphore(CONCURRENCY)
    kinds = requested_accommodation_kinds(state.get("accommodation_type"))
    jobs: list[tuple] = []  # (dest_iata, date_from, date_to, accommodation_kind, coroutine)
    for dest in state.get("destinations", []):
        iata = dest["iata"]
        packages[iata] = []
        # A package search can only be scoped by destination, not by a separately resolved
        # stay area without also moving the flight destination. With an explicit area, skip
        # generic city-wide packages and let the optimizer combine city flights with the
        # area-specific hotel/home results from hotel_node.
        if (state.get("accommodation_area") or "").strip():
            continue
        for date_from, date_to in slots:
            for accommodation_kind in kinds:
                # lastminute hotel/package tools require `adults` as a STRING (flights wants int).
                jobs.append((iata, date_from, date_to, accommodation_kind, bounded_call(
                    mcp, SEARCH, {"origin": origin, "destination": iata, "date_from": date_from,
                                  "date_to": date_to or "", "adults": str(adults), "lang": "it",
                                  "accommodation_type": ACCOMMODATION_FILTERS[accommodation_kind]},
                    sem)))
    raws = await asyncio.gather(*(j[-1] for j in jobs))
    for (iata, date_from, date_to, accommodation_kind, _), raw in zip(jobs, raws):
        for o in normalize_packages(raw, adults, accommodation_kind):
            o["date_from"], o["date_to"] = date_from, date_to
            packages[iata].append(o)
    return {"packages": packages}
