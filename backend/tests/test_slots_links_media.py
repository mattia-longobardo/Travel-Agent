import pytest
from app.agent.slots import enumerate_slots, slots_for_state, MAX_SLOTS
from app.agent.links import (
    booking_fallback_url, HOTEL_FALLBACK_URL, FLIGHT_FALLBACK_URL, PACKAGE_FALLBACK_URL,
    hotel_review_url,
)
from app.agent.media import first_image
from app.agent.nodes.optimizer import optimizer_node


# --- slots -------------------------------------------------------------------

def test_max_slots_allows_four_periods():
    assert MAX_SLOTS >= 4

def test_enumerate_slots_caps_and_keeps_nights():
    slots = enumerate_slots("2026-08-18", "2026-08-31", nights=7, max_slots=4)
    assert 2 <= len(slots) <= 4
    assert slots[0][0] == "2026-08-18"            # window start
    assert all((__import__("datetime").date.fromisoformat(b)
                - __import__("datetime").date.fromisoformat(a)).days == 7 for a, b in slots)
    # last slot must end no later than the window
    assert slots[-1][1] <= "2026-08-31"

def test_enumerate_slots_single_when_no_slack():
    slots = enumerate_slots("2026-08-18", "2026-08-25", nights=7)
    assert slots == [("2026-08-18", "2026-08-25")]

def test_slots_for_state_single_when_not_flexible():
    state = {"date_from": "2026-08-18", "date_to": "2026-08-25", "dates_flexible": False}
    assert slots_for_state(state) == [("2026-08-18", "2026-08-25")]

def test_slots_for_state_fans_out_when_flexible():
    state = {"date_from": "2026-08-18", "date_to": "2026-08-25", "dates_flexible": True,
             "window_from": "2026-08-18", "window_to": "2026-08-31", "trip_nights": 7}
    slots = slots_for_state(state)
    assert len(slots) >= 2
    assert len({s[0] for s in slots}) == len(slots)   # distinct start dates


# --- links -------------------------------------------------------------------

from urllib.parse import urlparse

# The fallback must keep the user ON lastminute (no Google bounce). These section pages are
# search-indexed lastminute URLs that resolve for real users.
def test_fallback_urls_are_https_lastminute():
    for url in (HOTEL_FALLBACK_URL, FLIGHT_FALLBACK_URL, PACKAGE_FALLBACK_URL):
        assert url.startswith("https://")
        assert urlparse(url).netloc == "www.it.lastminute.com"
        assert "google" not in url

def test_booking_fallback_routes_by_kind():
    # hotel-only lands on the hotels section; package/separate on the flight+hotel section
    assert booking_fallback_url("hotel_only") == HOTEL_FALLBACK_URL
    assert booking_fallback_url("package") == PACKAGE_FALLBACK_URL
    assert booking_fallback_url("separate") == PACKAGE_FALLBACK_URL
    assert booking_fallback_url(None) == PACKAGE_FALLBACK_URL


def test_hotel_review_url_builds_verified_format():
    url = hotel_review_url(336937, 768510350, "TCI", "2026-07-26", "2026-07-30", 2)
    assert url == ("https://www.it.lastminute.com/s/tsx/336937?pageType=review"
                   "&destination=TCI&dateFrom=2026-07-26&dateTo=2026-07-30"
                   "&adults=2&vcSearchId=768510350&searchMode=HO")

def test_hotel_review_url_none_without_ids():
    assert hotel_review_url(None, 1, "TCI", "2026-07-26", "2026-07-30", 2) is None
    assert hotel_review_url(7, None, "TCI", "2026-07-26", "2026-07-30", 2) is None

def test_hotel_review_url_tolerates_missing_dest_code():
    url = hotel_review_url(7, 1, None, "2026-07-26", "2026-07-30", 2)
    assert url.startswith("https://www.it.lastminute.com/s/tsx/7?")
    assert "destination=" not in url  # omit empty dest rather than send destination=None


# --- media -------------------------------------------------------------------

def test_first_image_prefers_direct_url_then_lists_then_nested():
    assert first_image({"image": "https://x/y.jpg"}) == "https://x/y.jpg"
    assert first_image({"images": ["https://a/b.png"]}) == "https://a/b.png"
    assert first_image({"hotel": {"thumbnail": {"url": "https://h/t.jpg"}}}) == "https://h/t.jpg"
    assert first_image({"name": "no pics"}) is None


# --- optimizer: best period per destination ----------------------------------

@pytest.mark.asyncio
async def test_optimizer_picks_cheapest_period_per_destination():
    """Each destination should surface at its own best (cheapest) period, with dates."""
    state = {"budget_per_person": 2000, "currency": "EUR", "adults": 1, "min_stars": None,
             "destinations": [{"iata": "TFS", "name": "Tenerife"}],
             "flights": {"TFS": [
                 {"price_per_person": 200, "summary": "w1", "pricing_id": "f1",
                  "date_from": "2026-08-18", "date_to": "2026-08-25"},
                 {"price_per_person": 120, "summary": "w2", "pricing_id": "f2",
                  "date_from": "2026-08-24", "date_to": "2026-08-31"}]},
             "hotels": {"TFS": [
                 {"price_per_person": 300, "name": "H", "stars": 4, "rating": 8.0, "hotel_internal_id": 1,
                  "date_from": "2026-08-18", "date_to": "2026-08-25"},
                 {"price_per_person": 300, "name": "H", "stars": 4, "rating": 8.0, "hotel_internal_id": 1,
                  "date_from": "2026-08-24", "date_to": "2026-08-31"}]},
             "packages": {}}
    out = await optimizer_node(state)
    ranked = out["ranked"]
    assert ranked[0]["price_per_person"] == 420            # 120 + 300, the cheaper week
    assert ranked[0]["date_from"] == "2026-08-24"
    assert ranked[0]["nights"] == 7
