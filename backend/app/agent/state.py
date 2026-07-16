# backend/app/agent/state.py
from typing import TypedDict, Optional, Annotated

def _merge(a: dict | None, b: dict | None) -> dict:
    return {**(a or {}), **(b or {})}

class TravelState(TypedDict, total=False):
    chat_id: int
    messages: list
    origin_coords: Optional[tuple]
    origin_iata: list
    destinations: list
    scout_candidates: list
    shown_destinations: list
    selected_destination: Optional[str]
    selected_pool: list
    generate_more: bool
    refine_text: Optional[str]
    search_mode: Optional[str]  # "flight_hotel" (default) | "hotel_only" | "flight_only"
    accommodation_type: Optional[str]  # "hotel" | "home" | "both" (default)
    accommodation_area: Optional[str]  # specific neighbourhood/area for the stay search
    scout_rounds: int
    date_from: Optional[str]
    date_to: Optional[str]
    window_from: Optional[str]
    window_to: Optional[str]
    trip_nights: Optional[int]
    dates_flexible: bool
    adults: int
    children_ages: list
    budget_per_person: Optional[float]
    currency: str
    min_stars: Optional[int]
    preferred_hotels: list
    no_flight: bool
    constraints: dict
    preferences_asked: bool
    missing: list
    pending_question: Optional[dict]
    prefill: Optional[dict]
    flights: Annotated[dict, _merge]
    hotels: Annotated[dict, _merge]
    packages: Annotated[dict, _merge]
    ranked: list
    final_message: str
