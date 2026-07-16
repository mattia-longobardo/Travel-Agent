"""Booking-link helpers.

The lastminute MCP mints a real deep-link via ``generate_booking_link`` when we hold the
right ids (packages carry both ``pricing_id`` and ``rate_id``; "separate" combos and
hotel-only cards often do not). When minting is not possible we still keep the user **on
lastminute** (decision 2026-06-21 — previously we bounced to a Google search) by routing to
the relevant lastminute *section* landing page for the card type.

We deliberately do NOT build a pre-filled lastminute deep-search URL: that query format is
undocumented and historically returned 403/404, and lastminute 403s bots so it cannot be
verified. The section pages below are stable, search-indexed lastminute URLs that always
resolve for a real user (no destination/date pre-fill, but always the right product). Centralised
here so swapping in a confirmed pre-filled search path later is a one-line change.
"""

from urllib.parse import urlencode

_LM_BASE = "https://www.it.lastminute.com"

# Stable, search-indexed lastminute section landing pages (verified to exist; the bare domain
# 403s bots but these resolve for real users). Not pre-filled with destination/dates.
HOTEL_FALLBACK_URL = f"{_LM_BASE}/hotels/cheap"
FLIGHT_FALLBACK_URL = f"{_LM_BASE}/flights"
PACKAGE_FALLBACK_URL = f"{_LM_BASE}/city-breaks/flight-hotel"


def booking_fallback_url(kind: str | None) -> str:
    """The lastminute section URL to use for a card's primary booking button when no real
    deep-link could be minted. Routes by card kind so the click still lands on the right
    product: hotel-only → hotels, everything else (package / separate combo) → flight+hotel."""
    if kind == "hotel_only":
        return HOTEL_FALLBACK_URL
    return PACKAGE_FALLBACK_URL


def hotel_review_url(hotel_internal_id, search_id, lm_dest_code,
                     date_from, date_to, adults) -> str | None:
    """Verified lastminute hotel review URL (dated, hotel-specific) built from ids the card
    already carries. Returns None if the required ids are missing."""
    if not hotel_internal_id or not search_id:
        return None
    params = [("pageType", "review")]
    if lm_dest_code:
        params.append(("destination", lm_dest_code))
    if date_from:
        params.append(("dateFrom", date_from))
    if date_to:
        params.append(("dateTo", date_to))
    params.append(("adults", str(adults or 1)))
    params.append(("vcSearchId", str(search_id)))
    params.append(("searchMode", "HO"))
    return f"{_LM_BASE}/s/tsx/{hotel_internal_id}?{urlencode(params)}"


def property_presentation_url(hotel_internal_id, search_id, date_from, date_to,
                              accommodation_kind: str | None = None, *, name=None,
                              destination=None, image_url=None, stars=None, rating=None) -> str | None:
    """Internal, non-booking presentation page for a property.

    The public lastminute ``/s/tsx`` URL is a dated sales funnel even with
    ``pageType=review``. The app instead opens its own details page and lazily reads the
    provider's hotel description, gallery and policies through ``select_hotel_options``.
    """
    if not hotel_internal_id or not search_id or not date_from or not date_to:
        return None
    params = {
        "search_id": str(search_id),
        "date_from": str(date_from),
        "date_to": str(date_to),
        "kind": "home" if accommodation_kind == "home" else "hotel",
    }
    for key, value in {
        "name": name, "destination": destination, "image": image_url,
        "stars": stars, "rating": rating,
    }.items():
        if value not in (None, ""):
            params[key] = str(value)
    return f"/stays/{hotel_internal_id}?{urlencode(params)}"


def italian_storefront_url(url: str | None) -> str | None:
    """Keep lastminute sales links on the Italian/EUR storefront."""
    if not url:
        return None
    from urllib.parse import urlparse, urlunparse
    try:
        parsed = urlparse(url)
    except Exception:
        return url
    host = (parsed.hostname or "").lower()
    if host in {"lastminute.com", "www.lastminute.com", "lastminute.ie", "www.lastminute.ie"}:
        netloc = "www.it.lastminute.com"
        if parsed.port:
            netloc += f":{parsed.port}"
        return urlunparse(parsed._replace(netloc=netloc))
    return url
