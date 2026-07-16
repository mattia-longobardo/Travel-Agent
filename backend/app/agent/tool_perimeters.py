NS = "lastminute__"

PERIMETERS: dict[str, list[str]] = {
    "flight": [NS + "search_flights", NS + "get_alternative_flights",
               NS + "change_flight", NS + "resolve_destination_id"],
    "hotel": [NS + "search_only_hotel", NS + "select_hotel_options",
              NS + "resolve_destination_id"],
    "package": [NS + "search_flight_and_hotel_package", NS + "resolve_destination_id"],
    "presenter": [NS + "generate_booking_link"],
    "intake": [],
    "scout": [],
    "optimizer": [],
}

def filter_tools(all_tools: list[dict], agent: str) -> list[dict]:
    allowed = set(PERIMETERS.get(agent, []))
    return [t for t in all_tools if t.get("function", {}).get("name") in allowed]
