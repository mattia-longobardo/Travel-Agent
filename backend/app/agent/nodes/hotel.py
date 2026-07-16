import asyncio
import json
import re
import unicodedata
from app.agent.accommodation import ACCOMMODATION_FILTERS, requested_accommodation_kinds
from app.agent.currency import EUR, is_eur_offer
from app.agent.media import first_image
from app.agent.identity import extract_destination_code, extract_hotel_id, extract_search_id
from app.agent.price import parse_price
from app.agent.search import CONCURRENCY, bounded_call
from app.agent.slots import slots_for_state
from app.agent.tool_perimeters import NS

SEARCH = NS + "search_only_hotel"
RESOLVE_DESTINATION = NS + "resolve_destination_id"
SELECT_HOTEL = NS + "select_hotel_options"

# A neighbourhood that is not a standalone lastminute destination requires a city search
# followed by validation against the provider's property details. Keep the candidate pool wide
# enough to find useful matches while bounding the extra detail calls and overall latency.
AREA_MAX_RESULTS = 20
AREA_DETAIL_LIMIT = 12


def _parse(raw: str) -> tuple[object, list[dict]]:
    """Return (top-level object, product items). The top-level ``search_id`` is needed to
    later mint a booking link via select_hotel_options -> generate_booking_link."""
    try:
        data = json.loads(raw)
    except Exception:
        return None, []
    if isinstance(data, dict):
        items = data.get("products_summary") or data.get("results") or data.get("hotels") or []
        return data, (items if isinstance(items, list) else [])
    return data, (data if isinstance(data, list) else [])


def _items(raw: str) -> list[dict]:
    return _parse(raw)[1]


def _name_matches(name: str | None, preferred: list[str]) -> bool:
    n = (name or "").lower()
    return any(p.lower().strip() in n for p in preferred if p.strip())


def _plain(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch)).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def _resolved_destination_id(raw: str, requested_name: str | None = None) -> str | None:
    """Extract an exact lastminute destination id from resolve_destination_id output."""
    try:
        data = json.loads(raw)
    except Exception:
        return None
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        return None
    if data.get("success"):
        destination_id = data.get("id") or data.get("destination_id")
        return str(destination_id) if destination_id not in (None, "") else None

    # The provider often returns an exact textual match under ``suggestions`` while setting
    # success=false (for example Roma -> the first suggestion named Roma). Accept only a name
    # equal to the requested place; never silently turn "Trastevere, Roma" into all of Roma.
    requested = _plain(requested_name)
    requested_area = _plain((requested_name or "").split(",", 1)[0])
    targets = {value for value in (requested, requested_area) if value}
    for suggestion in data.get("suggestions") or []:
        if not isinstance(suggestion, dict) or _plain(suggestion.get("name")) not in targets:
            continue
        destination_id = suggestion.get("id") or suggestion.get("destination_id")
        if destination_id not in (None, ""):
            return str(destination_id)
    return None


async def _resolve_area(mcp, sem: asyncio.Semaphore, area: str, city: str | None) -> str | None:
    """Resolve a requested stay area, using the city to disambiguate repeated area names.

    lastminute's resolver accepts destination names rather than arbitrary coordinates. Many
    tourism areas (for example Costa Adeje) are destinations in their own right; a second
    area+city query covers ambiguous names when the source supports that form. If neither is
    resolved, the caller retains the original city/IATA search instead of failing the run.
    """
    queries = []
    if city and city.strip().lower() not in area.strip().lower():
        # Disambiguate repeated area names (for example "Centro storico") with the city first.
        queries.append(f"{area.strip()}, {city.strip()}")
    queries.append(area.strip())
    for query in queries:
        raw = await bounded_call(
            mcp, RESOLVE_DESTINATION, {"lang": "it", "city_name": query}, sem,
        )
        resolved = _resolved_destination_id(raw, query)
        if resolved:
            return resolved
    return None


_AREA_STOPWORDS = {"zona", "quartiere", "rione", "district", "area", "centro", "city"}


def _area_terms(area: str, city: str | None) -> list[str]:
    city_terms = set(_plain(city).split())
    terms = [part for part in _plain(area).split()
             if part not in _AREA_STOPWORDS and part not in city_terms and len(part) > 2]
    # "centro storico" must still retain a useful token after dropping the generic "centro".
    return terms or [part for part in _plain(area).split() if len(part) > 2]


def _matches_area(text: str | None, area: str, city: str | None) -> bool:
    haystack = _plain(text)
    terms = _area_terms(area, city)
    return bool(haystack and terms and all(term in haystack for term in terms))


def _property_detail_text(raw: str) -> str:
    try:
        data = json.loads(raw)
    except Exception:
        return ""
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        return ""
    hotel = data.get("hotel") or {}
    if not isinstance(hotel, dict):
        return ""
    return " ".join(str(hotel.get(key) or "") for key in ("name", "address", "description"))


def normalize_hotels(raw: str, adults: int = 1, min_stars: int | None = None,
                     preferred=None) -> list[dict]:
    """lastminute returns the hotel price as the TOTAL for the stay/room; divide by adults.

    When ``preferred`` names are given and at least one offer matches, keep ONLY the matches
    (the user named a specific hotel); otherwise keep the full list — never empty on a miss."""
    preferred = preferred or []
    adults = max(adults or 1, 1)
    data, items = _parse(raw)
    out = []
    for it in items:
        if not is_eur_offer(it, data):
            continue
        stars = it.get("stars") or it.get("category")
        if min_stars and (stars or 0) < min_stars:
            continue
        total = parse_price(it.get("price_total"))
        if total is None and it.get("price") is not None:
            total = parse_price(it.get("price"))  # legacy/per-person field
        pp = round(total / adults, 2) if total is not None else None
        out.append({"price_per_person": pp,
                    "currency": EUR,
                    "name": it.get("name"),
                    "stars": stars,
                    "rating": it.get("rating"),
                    "hotel_reviews": it.get("reviews"),
                    "hotel_distance_km": it.get("distance_km"),
                    "hotel_facilities": [value.strip() for value in (it.get("facilities") or [])
                                         if isinstance(value, str) and value.strip()],
                    # Preserve False: it means the displayed rate is explicitly non-cancellable.
                    "hotel_cancellable": it.get("cancellable"),
                    "image_url": first_image(it),
                    "search_id": extract_search_id(data, it),
                    "lm_dest_code": extract_destination_code(data, it),
                    "hotel_internal_id": extract_hotel_id(it, allow_item_id=True)})
    out = [h for h in out if h["price_per_person"] is not None]
    if preferred:
        matched = [h for h in out if _name_matches(h["name"], preferred)]
        if matched:        # only filter when it actually matches something
            return matched
    return out


async def hotel_node(state, llm=None, mcp=None) -> dict:
    hotels: dict[str, list[dict]] = {}
    if mcp is None:
        return {"hotels": hotels}
    adults = state.get("adults", 1) or 1
    slots = slots_for_state(state)
    sem = asyncio.Semaphore(CONCURRENCY)
    kinds = requested_accommodation_kinds(state.get("accommodation_type"))
    area = (state.get("accommodation_area") or "").strip()
    destinations = state.get("destinations", [])
    if area:
        resolved_areas = await asyncio.gather(*(
            _resolve_area(mcp, sem, area, dest.get("name")) for dest in destinations
        ))
        # When the neighbourhood is not a provider destination, resolve the parent city so the
        # broad availability search uses a real lastminute destination id rather than a weak IATA
        # fallback. Results are subsequently validated against name/address/description.
        resolved_cities = await asyncio.gather(*(
            _resolve_area(mcp, sem, dest.get("name") or dest.get("iata", ""), None)
            if not resolved_area else asyncio.sleep(0, result=None)
            for dest, resolved_area in zip(destinations, resolved_areas)
        ))
    else:
        resolved_areas = [None] * len(destinations)
        resolved_cities = [None] * len(destinations)
    search_destinations: dict[str, str] = {}
    area_filter_required: dict[str, bool] = {}
    city_names: dict[str, str | None] = {}
    for dest, resolved_area, resolved_city in zip(destinations, resolved_areas, resolved_cities):
        iata = dest["iata"]
        # Keep the result map keyed by the original IATA so flights and area-specific stays
        # still join in the optimizer. Only the MCP search argument changes to the area id.
        search_destinations[iata] = resolved_area or resolved_city or iata
        area_filter_required[iata] = bool(area and not resolved_area)
        city_names[iata] = dest.get("name")
    jobs: list[tuple] = []  # (dest_iata, date_from, date_to, accommodation_kind, coroutine)
    for dest in destinations:
        iata = dest["iata"]
        hotels[iata] = []
        for date_from, date_to in slots:
            for accommodation_kind in kinds:
                # lastminute hotel/package tools require `adults` as a STRING (flights wants int).
                args = {"destination": search_destinations[iata], "date_from": date_from,
                        "date_to": date_to or "", "adults": str(adults), "lang": "it",
                        "accommodation_type": ACCOMMODATION_FILTERS[accommodation_kind]}
                if area_filter_required[iata]:
                    args["max_results"] = AREA_MAX_RESULTS
                jobs.append((iata, date_from, date_to, accommodation_kind,
                             bounded_call(mcp, SEARCH, args, sem)))
    raws = await asyncio.gather(*(j[-1] for j in jobs))
    detail_jobs: list[tuple] = []  # (iata, offer, coroutine)
    for (iata, date_from, date_to, accommodation_kind, _), raw in zip(jobs, raws):
        # Star ratings apply to hotel/resort results only. Applying them to homes would drop
        # apartments and villas that legitimately have no hotel-star classification.
        min_stars = state.get("min_stars") if accommodation_kind == "hotel" else None
        candidates = normalize_hotels(raw, adults, min_stars, state.get("preferred_hotels"))
        detail_count = 0
        for o in candidates:
            o["date_from"], o["date_to"] = date_from, date_to
            o["accommodation_kind"] = accommodation_kind
            if not area_filter_required[iata]:
                hotels[iata].append(o)
                continue
            if _matches_area(o.get("name"), area, city_names[iata]):
                hotels[iata].append(o)
                continue
            sid, hid = o.get("search_id"), o.get("hotel_internal_id")
            if sid and hid and detail_count < AREA_DETAIL_LIMIT:
                try:
                    sid_arg, hid_arg = int(sid), int(hid)
                except (TypeError, ValueError):
                    continue
                detail_count += 1
                detail_jobs.append((iata, o, bounded_call(mcp, SELECT_HOTEL, {
                    "search_id": sid_arg, "hotel_internal_id": hid_arg,
                    "date_from": date_from, "date_to": date_to,
                }, sem)))

    if detail_jobs:
        detail_raws = await asyncio.gather(*(job[-1] for job in detail_jobs))
        for (iata, offer, _), detail_raw in zip(detail_jobs, detail_raws):
            if _matches_area(_property_detail_text(detail_raw), area, city_names[iata]):
                hotels[iata].append(offer)
    return {"hotels": hotels}
