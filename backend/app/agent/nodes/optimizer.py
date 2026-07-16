from datetime import date
from app.agent.currency import EUR, is_eur_offer
from app.agent.price import parse_price


def _nights(date_from, date_to, fallback: int = 7) -> int:
    try:
        d1 = date.fromisoformat(date_from); d2 = date.fromisoformat(date_to)
        return max((d2 - d1).days, 1)
    except (TypeError, ValueError):
        return fallback


def _group_by_slot(offers: list[dict]) -> dict[tuple, list[dict]]:
    groups: dict[tuple, list[dict]] = {}
    for o in offers:
        groups.setdefault((o.get("date_from"), o.get("date_to")), []).append(o)
    return groups


MAX_PER_DEST = 10


def _combine_flight_hotel(dest, f, h) -> dict:
    """Pair one flight with one hotel into a 'separate' card."""
    pp = round(f["price_per_person"] + h["price_per_person"], 2)
    date_from = f.get("date_from") or h.get("date_from")
    date_to = f.get("date_to") or h.get("date_to")
    return {"kind": "separate", "destination": f"{dest['name']} ({dest['iata']})",
            "dest_iata": dest["iata"], "dest_name": dest["name"],
            "currency": EUR,
            "price_per_person": pp, "flight_pp": f["price_per_person"], "hotel_pp": h["price_per_person"],
            "hotel_name": h.get("name"), "hotel_stars": h.get("stars"),
            "hotel_rating": h.get("rating"), "accommodation_kind": h.get("accommodation_kind", "hotel"),
            "hotel_reviews": h.get("hotel_reviews"),
            "hotel_distance_km": h.get("hotel_distance_km"),
            "hotel_facilities": h.get("hotel_facilities") or [],
            "hotel_cancellable": h.get("hotel_cancellable"),
            "flight_summary": f.get("summary", ""),
            "departure_iata": f.get("departure_iata"),
            "image_url": h.get("image_url"), "date_from": date_from, "date_to": date_to,
            # booking link: hotel chain (search_id + hotel id) with the flight deeplink as fallback.
            "_pricing_id": None, "_rate_id": None,
            "_search_id": h.get("search_id"), "_hotel_internal_id": h.get("hotel_internal_id"),
            "_lm_dest_code": h.get("lm_dest_code"),
            "_flight_deeplink": f.get("deeplink")}


def combine_separate(dest, flights, hotels) -> dict | None:
    """Combine the cheapest flight with the best-rated hotel of the SAME period."""
    flights = [offer for offer in flights if is_eur_offer(offer)]
    hotels = [offer for offer in hotels if is_eur_offer(offer)]
    if not flights or not hotels:
        return None
    f = min((x for x in flights if x.get("price_per_person") is not None),
            key=lambda x: x["price_per_person"], default=None)
    h = max((x for x in hotels if x.get("price_per_person") is not None),
            key=lambda x: (x.get("rating") or 0), default=None)
    if not f or not h:
        return None
    return _combine_flight_hotel(dest, f, h)


def _from_package(dest, p) -> dict:
    return {"kind": "package", "destination": f"{dest['name']} ({dest['iata']})",
            "dest_iata": dest["iata"], "dest_name": dest["name"],
            "currency": EUR,
            "price_per_person": p.get("price_per_person"), "price_total": p.get("price_total"),
            "flight_pp": None, "hotel_pp": None,
            "hotel_name": p.get("hotel_name"), "hotel_stars": p.get("hotel_stars"),
            "hotel_rating": p.get("hotel_rating"),
            "hotel_reviews": p.get("hotel_reviews"),
            "hotel_distance_km": p.get("hotel_distance_km"),
            "hotel_facilities": p.get("hotel_facilities") or [],
            "hotel_cancellable": p.get("hotel_cancellable"),
            "accommodation_kind": p.get("accommodation_kind", "hotel"),
            "flight_summary": p.get("flight_summary", ""),
            "departure_iata": p.get("departure_iata"),
            "image_url": p.get("image_url"), "date_from": p.get("date_from"), "date_to": p.get("date_to"),
            "_pricing_id": p.get("pricing_id"), "_rate_id": p.get("rate_id"),
            "_search_id": p.get("search_id"), "_hotel_internal_id": p.get("hotel_internal_id"),
            "_lm_dest_code": p.get("lm_dest_code"),
            "_flight_carrier": p.get("flight_carrier")}


def _from_flight(dest, f) -> dict:
    """Build a flight-only card (the user asked for flights only, no hotel)."""
    return {"kind": "flight_only", "destination": f"{dest['name']} ({dest['iata']})",
            "dest_iata": dest["iata"], "dest_name": dest["name"],
            "currency": EUR,
            "price_per_person": f.get("price_per_person"),
            "flight_pp": f.get("price_per_person"), "hotel_pp": None,
            "hotel_name": None, "hotel_stars": None, "hotel_rating": None,
            "accommodation_kind": None,
            "flight_summary": f.get("summary", ""), "airline": f.get("airline"),
            "departure_iata": f.get("departure_iata"),
            "image_url": None, "date_from": f.get("date_from"), "date_to": f.get("date_to"),
            "_pricing_id": None, "_rate_id": None,
            "_search_id": None, "_hotel_internal_id": None, "_lm_dest_code": None,
            "_flight_deeplink": f.get("deeplink")}


def _from_hotel(dest, h) -> dict:
    """Build a hotel-only card (overland trip, no flight)."""
    return {"kind": "hotel_only", "destination": f"{dest['name']} ({dest['iata']})",
            "dest_iata": dest["iata"], "dest_name": dest["name"],
            "currency": EUR,
            "price_per_person": h.get("price_per_person"),
            "flight_pp": None, "hotel_pp": h.get("price_per_person"),
            "hotel_name": h.get("name"), "hotel_stars": h.get("stars"),
            "hotel_rating": h.get("rating"),
            "hotel_reviews": h.get("hotel_reviews"),
            "hotel_distance_km": h.get("hotel_distance_km"),
            "hotel_facilities": h.get("hotel_facilities") or [],
            "hotel_cancellable": h.get("hotel_cancellable"),
            "accommodation_kind": h.get("accommodation_kind", "hotel"), "flight_summary": "",
            "departure_iata": None, "image_url": h.get("image_url"),
            "date_from": h.get("date_from"), "date_to": h.get("date_to"),
            "_pricing_id": None, "_rate_id": None,
            "_search_id": h.get("search_id"), "_hotel_internal_id": h.get("hotel_internal_id"),
            "_lm_dest_code": h.get("lm_dest_code"),
            "_flight_deeplink": None}


def _hotel_key(card, fallback_idx: int):
    """Card identity for dedup. Hotels: internal id, else case-insensitive name. Flight-only
    cards: the flight summary (same itinerary at two periods keeps the cheapest). Unknown
    identity falls back to a unique index (never collapsed together)."""
    if card.get("kind") == "flight_only":
        summary = (card.get("flight_summary") or "").strip().lower()
        return ("flight", summary) if summary else ("idx", fallback_idx)
    hid = card.get("_hotel_internal_id")
    if hid is not None:
        return ("id", hid)
    name = (card.get("hotel_name") or "").strip().lower()
    if name:
        return ("name", name)
    return ("idx", fallback_idx)


def _candidates_for_dest(dest, flights, hotels, packages, mode="flight_hotel") -> list[dict]:
    """All candidate cards for a destination, deduped by hotel (or flight itinerary).

    ``mode`` selects what the user asked for:
    - "flight_hotel" (default): for each period, pair every hotel with the cheapest flight of
      that period (so distinct hotels surface, not just the best-rated one), and add every
      package. When a period has hotels but NO flight, fall back to hotel-only cards instead
      of silently dropping the hotels (a flight-search failure must not empty the results).
    - "hotel_only" (incl. overland/no_flight trips): hotel-only cards, no flight pairing.
    - "flight_only": one card per flight offer, no hotels/packages.

    Cards are then grouped by identity and only the CHEAPEST card per hotel/itinerary is kept.
    Returns up to MAX_PER_DEST distinct cards, cheapest first."""
    # Normalizers already drop non-EUR offers, but keep this boundary defensive because
    # checkpointed/legacy state and tests may feed the optimizer directly. Missing currency is
    # the documented legacy EUR case; an explicit GBP/USD offer is never combined or relabelled.
    fby = _group_by_slot([offer for offer in flights if is_eur_offer(offer)])
    hby = _group_by_slot([offer for offer in hotels if is_eur_offer(offer)])
    pby = _group_by_slot([offer for offer in packages if is_eur_offer(offer)])
    options: list[dict] = []
    for slot in set(fby) | set(hby) | set(pby):
        if mode == "hotel_only":
            options.extend(_from_hotel(dest, h) for h in hby.get(slot, [])
                           if h.get("price_per_person") is not None)
            continue
        if mode == "flight_only":
            options.extend(_from_flight(dest, f) for f in fby.get(slot, [])
                           if f.get("price_per_person") is not None)
            continue
        slot_flights = [x for x in fby.get(slot, []) if x.get("price_per_person") is not None]
        cheapest_flight = min(slot_flights, key=lambda x: x["price_per_person"], default=None)
        if cheapest_flight:
            for h in hby.get(slot, []):
                if h.get("price_per_person") is not None:
                    options.append(_combine_flight_hotel(dest, cheapest_flight, h))
        else:
            # No flight found for this period (bad IATA, MCP error, sold out): surface the
            # hotels as hotel-only cards rather than discarding them and reporting "nothing".
            options.extend(_from_hotel(dest, h) for h in hby.get(slot, [])
                           if h.get("price_per_person") is not None)
        options.extend(_from_package(dest, p) for p in pby.get(slot, []))
    options = [o for o in options if o.get("price_per_person") is not None]

    # Dedup by hotel: keep the cheapest period per hotel.
    best_by_hotel: dict = {}
    for i, o in enumerate(options):
        key = _hotel_key(o, i)
        cur = best_by_hotel.get(key)
        if cur is None or o["price_per_person"] < cur["price_per_person"]:
            best_by_hotel[key] = o

    deduped = sorted(best_by_hotel.values(), key=lambda o: o["price_per_person"])
    return deduped[:MAX_PER_DEST]


def _unmet(card, budget, min_stars) -> list[str]:
    warnings: list[str] = []
    pp = card.get("price_per_person")
    if isinstance(budget, (int, float)) and isinstance(pp, (int, float)) and pp > budget:
        warnings.append(f"Supera il budget di {round(pp - budget)}€ a persona")
    if card.get("kind") == "flight_only":
        return warnings  # no hotel on the card: the star constraint does not apply
    if card.get("accommodation_kind") == "home":
        return warnings  # homes/villas/apartments legitimately have no hotel-star classification
    stars = card.get("hotel_stars")
    if isinstance(min_stars, (int, float)) and min_stars and (stars or 0) < min_stars:
        warnings.append(f"Hotel {stars or '?'}★, sotto le {min_stars}★ richieste")
    return warnings


async def optimizer_node(state) -> dict:
    # Budget/stars may arrive as free text ("quel che serve") — coerce defensively so the
    # numeric comparisons below never crash; a non-numeric value means "no constraint".
    budget = parse_price(state.get("budget_per_person"))
    min_stars = state.get("min_stars")
    if not isinstance(min_stars, int):
        min_stars = parse_price(min_stars)
        min_stars = int(min_stars) if min_stars is not None else None
    mode = state.get("search_mode") or "flight_hotel"
    if state.get("no_flight"):
        mode = "hotel_only"
    destinations = state.get("destinations", [])
    fallback_nights = state.get("trip_nights") or _nights(state.get("date_from"), state.get("date_to"))

    per_dest: list[dict] = []
    for dest in destinations:
        iata = dest["iata"]
        per_dest.append(_candidates_for_dest(
            dest,
            state.get("flights", {}).get(iata, []),
            state.get("hotels", {}).get(iata, []),
            state.get("packages", {}).get(iata, []),
            mode=mode,
        ))

    # Each destination contributes up to MAX_PER_DEST distinct hotels (cheapest first, deduped by
    # hotel). Cheapest first overall; over-budget ones are NOT hidden — they are flagged instead
    # (the user always sees why a card breaks a constraint). The global safety cap only guards
    # against pathological fan-outs and is sized so it never drops below MAX_PER_DEST per location.
    SOFT_CAP = max(60, MAX_PER_DEST * len(destinations))
    flat = [c for cands in per_dest for c in cands]
    flat.sort(key=lambda c: c["price_per_person"])
    chosen = flat[:SOFT_CAP]

    ranked = []
    for i, c in enumerate(chosen):
        nights = _nights(c.get("date_from"), c.get("date_to"), fallback_nights)
        c2 = {"id": f"pkg-{i+1}", "nights": nights,
              "badge": "cheapest" if i == 0 else None, "reason": "",
              "unmet": _unmet(c, budget, min_stars), **c}
        # All accepted candidates are EUR. Set it explicitly after merging so a stale state/card
        # value can never make a GBP amount appear with an EUR label (or vice versa).
        c2["currency"] = EUR
        c2["price_total"] = c2.get("price_total") or round(c2["price_per_person"] * (state.get("adults", 1) or 1), 2)
        ranked.append(c2)
    if ranked and any(c.get("hotel_rating") for c in ranked):
        best = max(ranked, key=lambda c: (c.get("hotel_rating") or 0))
        if best["badge"] is None and not best["unmet"]:
            best["badge"] = "best_value"
    if ranked:
        if len(ranked) > 2 and ranked[-1]["badge"] is None and not ranked[-1]["unmet"]:
            ranked[-1]["badge"] = "upgrade"
    return {"ranked": ranked}
