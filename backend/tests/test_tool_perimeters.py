from app.agent.tool_perimeters import PERIMETERS, filter_tools

ALL = [{"type": "function", "function": {"name": n}} for n in [
    "lastminute__search_flights", "lastminute__get_alternative_flights",
    "lastminute__change_flight", "lastminute__search_only_hotel",
    "lastminute__select_hotel_options", "lastminute__search_flight_and_hotel_package",
    "lastminute__resolve_destination_id", "lastminute__generate_booking_link",
]]

def test_flight_perimeter_excludes_hotel_tools():
    names = {t["function"]["name"] for t in filter_tools(ALL, "flight")}
    assert "lastminute__search_flights" in names
    assert "lastminute__search_only_hotel" not in names
    assert "lastminute__search_flight_and_hotel_package" not in names

def test_package_perimeter_has_package_tool_only():
    names = {t["function"]["name"] for t in filter_tools(ALL, "package")}
    assert "lastminute__search_flight_and_hotel_package" in names
    assert "lastminute__search_flights" not in names

def test_every_perimeter_tool_exists_in_catalog():
    catalog = {t["function"]["name"] for t in ALL}
    for tools in PERIMETERS.values():
        for t in tools:
            assert t in catalog, f"{t} non nel catalogo MCP"
