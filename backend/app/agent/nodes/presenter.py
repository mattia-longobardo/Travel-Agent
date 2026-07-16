import asyncio
import json
from app.agent.links import (
    booking_fallback_url, hotel_review_url, property_presentation_url, italian_storefront_url,
    HOTEL_FALLBACK_URL, FLIGHT_FALLBACK_URL,
)
from app.agent.nodes.package import flight_details_summary, flight_summary_has_times
from app.agent.price import parse_price
from app.agent.tool_perimeters import NS

SYSTEM = ("Sei il Concierge. Riassumi in italiano, in 2-4 frasi, le proposte di viaggio trovate, "
          "evidenziando quella col miglior rapporto qualità/prezzo e l'alternativa più economica. "
          "Non elencare i prezzi uno per uno: le card li mostrano già. "
          "Le proposte elencate ESISTONO e sono mostrate all'utente: non dire mai che non ci sono "
          "soluzioni o che non hai trovato nulla. "
          "Non sollevare problemi di budget a meno che il riepilogo non indichi esplicitamente che "
          "alcune card superano il budget; in quel caso accennane il numero senza scoraggiare.")

BADGE_REASON = {
    "cheapest": "Opzione più economica entro il tuo budget.",
    "best_value": "Miglior rapporto qualità/prezzo (alloggio meglio recensito).",
    "upgrade": "Upgrade premium, vicino al tetto di spesa.",
    None: "Valida alternativa entro budget.",
}

# Minting a real checkout link costs two MCP round-trips (select_hotel_options +
# generate_booking_link), each spawning mcp-remote. We always TRY to mint a real deeplink for
# every card and only fall back (to the flight deeplink / a search URL) when the chain genuinely
# fails — a missing id, an MCP error, or a mint that exceeds _MINT_TIMEOUT (a slow/hung call is
# treated as a failure, never a block). Concurrency stays bounded so we don't fan out 100+
# subprocesses at once.
_CONCURRENCY = 8
_MINT_TIMEOUT = 12.0  # seconds per card; on timeout the card falls back instead of blocking


async def _resolve_ids(mcp, card) -> tuple[str | None, str | None, str | None]:
    """Resolve checkout ids and, for this exact package, any provider flight details.

    A package search can return only the carrier. In that case the exact
    ``select_hotel_options(search_id, hotel_internal_id, dates)`` response is also used to
    enrich the card. No separate flight search is consulted, so unrelated itineraries can never
    be combined with the package.
    """
    pid, rid = card.get("_pricing_id"), card.get("_rate_id")
    needs_flight_details = (
        card.get("kind") == "package"
        and not flight_summary_has_times(card.get("flight_summary"))
    )
    if pid and rid and not needs_flight_details:
        return str(pid), str(rid), None
    sid, hid = card.get("_search_id"), card.get("_hotel_internal_id")
    if not (mcp and sid and hid and card.get("date_from") and card.get("date_to")):
        return (str(pid) if pid else None, str(rid) if rid else None, None)
    try:
        raw = await mcp.call_tool(NS + "select_hotel_options", {
            "search_id": int(sid), "hotel_internal_id": int(hid),
            "date_from": card["date_from"], "date_to": card["date_to"]})
        data = json.loads(raw)
        if isinstance(data, list) and data:
            data = data[0]
        if not isinstance(data, dict):
            raise ValueError("invalid select_hotel_options payload")
        rooms = data.get("room_options") or []
        rid = rid or (rooms[0].get("rate_id") if rooms else None)
        pid = pid or data.get("pricing_id")
        enriched = None
        if needs_flight_details:
            enriched = flight_details_summary(data.get("flight_details")) or flight_details_summary(data)
        return (str(pid) if pid else None, str(rid) if rid else None, enriched)
    except Exception:
        pass
    return (str(pid) if pid else None, str(rid) if rid else None, None)


async def _generate_link(mcp, pricing_id, rate_id) -> str | None:
    try:
        raw = await mcp.call_tool(NS + "generate_booking_link",
                                  {"pricing_id": pricing_id, "rate_id": rate_id})
        data = json.loads(raw)
        if isinstance(data, list) and data:
            data = data[0]
        return italian_storefront_url(data.get("booking_url") or data.get("url"))
    except Exception:
        return None


async def _mint_link(mcp, card) -> tuple[str | None, str | None]:
    """Mint a real lastminute checkout URL for this card via the resolve→generate chain.
    For package cards this is the combined checkout; for separate cards it is the HOTEL
    checkout (the card carries search_id + hotel_internal_id). Always attempted when an MCP
    is available; returns None on failure or if the chain exceeds _MINT_TIMEOUT (so a slow or
    hung MCP call degrades to a fallback link instead of blocking the whole response)."""
    if not mcp:
        return None, None
    enriched_flight_summary = None
    try:
        async with asyncio.timeout(_MINT_TIMEOUT):
            pid, rid, enriched_flight_summary = await _resolve_ids(mcp, card)
            if pid and rid:
                return await _generate_link(mcp, pid, rid), enriched_flight_summary
            return None, enriched_flight_summary
    except Exception:  # incl. TimeoutError — a slow/hung mint degrades to a fallback link
        # Preserve exact-package flight data already returned by select_hotel_options even if
        # the later checkout-link generation fails or times out.
        return None, enriched_flight_summary


async def _resolve_urls(mcp, card, adults) -> tuple[
    str, str | None, str | None, str | None, str | None, str | None
]:
    """Return URLs plus an optional exact-package flight-summary enrichment.

    ``property_url`` is the app's internal, non-booking presentation page built from provider
    identities. ``review_url`` retains the dated lastminute sales URL only as a booking fallback
    and legacy compatibility field. ``hotel_url`` remains the hotel checkout URL for a separate
    flight+stay card.

    Fallback precedence for the primary booking link is: minted → review → section.

    - package / hotel_only: booking_url = minted checkout → review → the lastminute section
      fallback; flight_url/hotel_url = None.
    - separate: hotel_url = minted hotel checkout → review → the lastminute HOTELS section
      — never the flight (Bug: "Prenota hotel" must never open the flight booking). flight_url =
      the flight deeplink, falling back to the lastminute FLIGHTS section. booking_url = hotel_url.
    - flight_only: booking_url = flight_url = the flight deeplink → the lastminute FLIGHTS
      section; no hotel/review links and no mint round-trips (there is no hotel to mint).
    """
    if card.get("kind") == "flight_only":
        flight_url = italian_storefront_url(card.get("_flight_deeplink")) or FLIGHT_FALLBACK_URL
        return flight_url, flight_url, None, None, None, None
    review_url = hotel_review_url(card.get("_hotel_internal_id"), card.get("_search_id"),
                                  card.get("_lm_dest_code"), card.get("date_from"),
                                  card.get("date_to"), adults)
    property_url = property_presentation_url(
        card.get("_hotel_internal_id"), card.get("_search_id"),
        card.get("date_from"), card.get("date_to"), card.get("accommodation_kind"),
        name=card.get("hotel_name"), destination=card.get("dest_name") or card.get("destination"),
        image_url=card.get("image_url"), stars=card.get("hotel_stars"),
        rating=card.get("hotel_rating"),
    )
    minted, enriched_flight_summary = await _mint_link(mcp, card)
    if card.get("kind") == "separate":
        hotel_url = minted or review_url or HOTEL_FALLBACK_URL
        flight_url = italian_storefront_url(card.get("_flight_deeplink")) or FLIGHT_FALLBACK_URL
        return hotel_url, flight_url, hotel_url, property_url, review_url, None
    booking_url = minted or review_url or booking_fallback_url(card.get("kind"))
    return booking_url, None, None, property_url, review_url, enriched_flight_summary


def _package_flight_summary(card, enriched: str | None) -> str:
    """Always expose itinerary times or an explicit, truthful unavailable state."""
    if enriched and flight_summary_has_times(enriched):
        return enriched
    current = card.get("flight_summary")
    if isinstance(current, str):
        current = current.strip()
        if flight_summary_has_times(current) or current.startswith("Orari "):
            return current
    carrier = card.get("_flight_carrier")
    if carrier:
        return f"Orari non disponibili · Compagnia {carrier}"
    if current:
        return f"Orari non disponibili · {current}"
    return "Orari del volo non disponibili"


async def presenter_node(state, llm, mcp=None) -> dict:
    ranked = state.get("ranked", [])
    if not ranked:
        # Bugs 2/3: empty results are a date/destination problem, never a budget one. The budget
        # never filters or hides cards, so it must never be blamed (and no "€" figure appears).
        area = (state.get("accommodation_area") or "").strip()
        scope = f" nella zona {area}" if area else ""
        msg = (f"Non ho trovato proposte{scope} per le date e la destinazione indicate. "
               "Vuoi spostare le date, allungare/accorciare il soggiorno o provare un'altra zona?")
        return {"final_message": msg, "ranked": []}

    # Bugs 2/3: ground the concierge with concrete facts so it can never claim "no solutions"
    # (cards exist) nor invent a budget problem. Only flag over-budget when cards actually exceed.
    budget = parse_price(state.get("budget_per_person"))
    cheapest = min(ranked, key=lambda c: c["price_per_person"])
    over_budget = sum(1 for c in ranked if c.get("unmet"))
    grounding = [
        f"Numero di proposte trovate: {len(ranked)} (tutte mostrate all'utente).",
        f"Più economica: {cheapest['destination']} a {cheapest['price_per_person']}€ a persona.",
    ]
    if any(c.get("hotel_rating") for c in ranked):
        best_value = max(ranked, key=lambda c: (c.get("hotel_rating") or 0))
        grounding.append(f"Miglior rapporto qualità/prezzo: {best_value['destination']} a "
                         f"{best_value['price_per_person']}€ a persona.")
    elif all(c.get("kind") == "flight_only" for c in ranked):
        grounding.append("Le proposte sono solo voli: nessun hotel incluso, non parlare di hotel.")
    else:
        grounding.append("Le proposte includono alloggi, ma non hanno un punteggio recensioni confrontabile.")
    if budget:
        if over_budget:
            grounding.append(f"{over_budget} proposte su {len(ranked)} superano il budget di "
                             f"{int(budget)}€ a persona; le altre rientrano.")
        else:
            grounding.append(f"Tutte le proposte rientrano nel budget di {int(budget)}€ a persona.")
    final = await llm.complete_text(SYSTEM, " ".join(grounding))

    adults = state.get("adults", 1) or 1
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def resolve(c):
        async with sem:
            return await _resolve_urls(mcp, c, adults)

    resolved = await asyncio.gather(*(resolve(c) for c in ranked))

    cards = []
    for c, (booking_url, flight_url, hotel_url, property_url, review_url,
            enriched_flight_summary) in zip(ranked, resolved):
        # flight_pp/hotel_pp/flight_url/hotel_url do not start with "_", so they survive stripping.
        card = {k: v for k, v in c.items() if not k.startswith("_")}
        if card.get("kind") == "package":
            card["flight_summary"] = _package_flight_summary(c, enriched_flight_summary)
        card["reason"] = card.get("reason") or BADGE_REASON.get(card.get("badge"))
        card["booking_url"] = booking_url
        card["flight_url"] = flight_url
        card["hotel_url"] = hotel_url
        # The property/details page is deliberately distinct from checkout URLs. ``review_url``
        # remains as a compatibility alias while clients migrate to the clearer property_url name.
        card["property_url"] = property_url
        card["review_url"] = review_url
        cards.append(card)
    return {"final_message": final, "ranked": cards}
