import json, pytest
from app.agent.nodes.hotel import hotel_node, normalize_hotels


def test_normalize_hotels_filters_stars():
    raw = json.dumps([{"name": "A", "stars": 3, "price": 400, "rating": 8.0, "id": 1},
                      {"name": "B", "stars": 4, "price": 500, "rating": 8.7, "id": 2}])
    res = normalize_hotels(raw, min_stars=4)
    assert [h["name"] for h in res] == ["B"]
    assert res[0]["hotel_internal_id"] == 2


def test_normalize_hotels_real_schema_total_divided_by_adults():
    raw = json.dumps({"products_summary": [
        {"internal_id_hotel": 7432692, "name": "Alua Tenerife", "stars": 4, "rating": 87,
         "reviews": 1240, "distance_km": 1.7,
         "facilities": ["Piscina", "Wi-Fi", "", None], "cancellable": False,
         "price_total": 769.11, "currency": "EUR"}]})
    res = normalize_hotels(raw, adults=3, min_stars=4)
    assert res[0]["name"] == "Alua Tenerife"
    assert res[0]["price_per_person"] == round(769.11 / 3, 2)
    assert res[0]["hotel_internal_id"] == 7432692
    assert res[0]["currency"] == "EUR"
    assert res[0]["hotel_reviews"] == 1240
    assert res[0]["hotel_distance_km"] == 1.7
    assert res[0]["hotel_facilities"] == ["Piscina", "Wi-Fi"]
    assert res[0]["hotel_cancellable"] is False


def test_normalize_hotels_keeps_only_eur_with_item_overriding_top_level():
    raw = json.dumps({"currency": "GBP", "products_summary": [
        {"internal_id_hotel": 1, "name": "GBP inherited", "price_total": 100},
        {"internal_id_hotel": 2, "name": "EUR item", "currency": "EUR", "price_total": 200},
    ]})
    result = normalize_hotels(raw)
    assert [h["name"] for h in result] == ["EUR item"]
    assert result[0]["currency"] == "EUR"

    item_gbp = json.dumps({"currency": "EUR", "products_summary": [
        {"internal_id_hotel": 3, "name": "GBP item", "currency": "gbp", "price_total": 100},
    ]})
    assert normalize_hotels(item_gbp) == []


def test_normalize_hotels_captures_search_id():
    """search_id is needed to mint a booking link (select_hotel_options -> generate_booking_link)."""
    raw = json.dumps({"search_id": 616020433, "products_summary": [
        {"internal_id_hotel": 7, "name": "Sea", "stars": 4, "rating": 85, "price_total": 600.0}]})
    res = normalize_hotels(raw, adults=2, min_stars=4)
    assert res[0]["search_id"] == 616020433


def test_normalize_hotels_captures_lm_dest_code():
    """lm_dest_code (search_params.destination) is the lastminute destination code, distinct
    from the airport IATA; needed to build the verified review URL."""
    raw = json.dumps({"search_id": 1, "search_params": {"destination": "TCI"},
                      "products_summary": [{"internal_id_hotel": 7, "name": "Sea",
                                            "stars": 4, "rating": 85, "price_total": 600.0}]})
    res = normalize_hotels(raw, adults=2, min_stars=4)
    assert res[0]["lm_dest_code"] == "TCI"


def test_normalize_hotels_reads_identity_from_item_and_nested_hotel():
    raw = json.dumps({"products_summary": [{
        "name": "Casa sul mare", "stars": 4, "rating": 90, "price_total": 500,
        "search": {"id": 987}, "hotel": {"id": 654},
        "search_params": {"destination": "ROM"},
    }]})
    res = normalize_hotels(raw)
    assert res[0]["search_id"] == 987
    assert res[0]["hotel_internal_id"] == 654
    assert res[0]["lm_dest_code"] == "ROM"


def test_normalize_hotels_prioritizes_preferred_name_match():
    raw = json.dumps([{"name": "Anantara Qasr Al Sareb", "stars": 5, "price": 800, "rating": 9.2, "id": 1},
                      {"name": "Generic Resort", "stars": 4, "price": 400, "rating": 8.0, "id": 2}])
    res = normalize_hotels(raw, adults=1, preferred=["anantara"])
    assert [h["name"] for h in res] == ["Anantara Qasr Al Sareb"]


def test_normalize_hotels_keeps_all_when_preferred_unmatched():
    raw = json.dumps([{"name": "Anantara Qasr Al Sareb", "stars": 5, "price": 800, "rating": 9.2, "id": 1},
                      {"name": "Generic Resort", "stars": 4, "price": 400, "rating": 8.0, "id": 2}])
    res = normalize_hotels(raw, adults=1, preferred=["nonexistent"])
    assert len(res) == 2  # never empties out because of an unmatched name filter


class FakeMcp:
    def __init__(self, result): self.result = result; self.calls = []
    async def call_tool(self, name, args): self.calls.append((name, args)); return self.result


class AreaMcp:
    def __init__(self, resolved=True, detail_matches=True):
        self.resolved = resolved
        self.detail_matches = detail_matches
        self.calls = []

    async def call_tool(self, name, args):
        self.calls.append((name, args))
        if name.endswith("resolve_destination_id"):
            if self.resolved and args["city_name"].startswith("Trastevere"):
                return json.dumps({"success": True, "id": "778899"})
            if args["city_name"] == "Roma":
                # The real provider commonly returns an exact city under suggestions while
                # success=false; the node must still use that destination id.
                return json.dumps({"success": False, "suggestions": [
                    {"id": "131028", "name": "Roma", "country": "Italia"},
                ]})
            return json.dumps({"success": False, "suggestions": []})
        if name.endswith("select_hotel_options"):
            address = "Via degli Orti di Trastevere 3" if self.detail_matches else "Via Veneto 1"
            return json.dumps({"success": True, "hotel": {
                "name": "Stay", "address": address, "description": "Alloggio disponibile",
            }})
        return json.dumps({"search_id": 1, "products_summary": [
            {"internal_id_hotel": 7, "name": "Stay", "stars": 4, "price_total": 600},
        ]})


@pytest.mark.asyncio
async def test_hotel_node_per_destination_uses_eur_lang():
    real = json.dumps({"products_summary": [
        {"internal_id_hotel": 7, "name": "Sea", "stars": 4, "rating": 85, "price_total": 600.0}]})
    mcp = FakeMcp(real)
    state = {"date_from": "2026-08-18", "date_to": "2026-08-25", "adults": 2,
             "min_stars": 4, "destinations": [{"iata": "TFS", "name": "Tenerife"}]}
    out = await hotel_node(state, mcp=mcp)
    assert out["hotels"]["TFS"][0]["name"] == "Sea"
    assert out["hotels"]["TFS"][0]["price_per_person"] == 300.0
    assert mcp.calls[0][1]["lang"] == "it" and mcp.calls[0][1]["destination"] == "TFS"
    assert mcp.calls[0][1]["adults"] == "2"  # hotel tool requires adults as a string
    assert [call[1]["accommodation_type"] for call in mcp.calls] == ["1,2", "3,6,7,9,14"]
    assert {item["accommodation_kind"] for item in out["hotels"]["TFS"]} == {"hotel", "home"}


@pytest.mark.asyncio
@pytest.mark.parametrize(("requested", "mcp_filter"), [
    ("hotel", "1,2"),
    ("home", "3,6,7,9,14"),
])
async def test_hotel_node_applies_requested_accommodation_filter(requested, mcp_filter):
    raw = json.dumps({"search_id": 1, "products_summary": [
        {"internal_id_hotel": 7, "name": "Stay", "stars": 4, "price_total": 600}]})
    mcp = FakeMcp(raw)
    state = {"date_from": "2026-08-18", "date_to": "2026-08-25", "adults": 2,
             "accommodation_type": requested,
             "destinations": [{"iata": "TFS", "name": "Tenerife"}]}
    out = await hotel_node(state, mcp=mcp)
    assert len(mcp.calls) == 1
    assert mcp.calls[0][1]["accommodation_type"] == mcp_filter
    assert out["hotels"]["TFS"][0]["accommodation_kind"] == requested


@pytest.mark.asyncio
async def test_home_results_are_not_removed_by_hotel_star_filter():
    raw = json.dumps({"search_id": 1, "products_summary": [
        {"internal_id_hotel": 7, "name": "Villa", "stars": None, "price_total": 600}]})
    mcp = FakeMcp(raw)
    state = {"date_from": "2026-08-18", "date_to": "2026-08-25", "adults": 2,
             "accommodation_type": "home", "min_stars": 4,
             "destinations": [{"iata": "TFS", "name": "Tenerife"}]}
    out = await hotel_node(state, mcp=mcp)
    assert [item["name"] for item in out["hotels"]["TFS"]] == ["Villa"]


@pytest.mark.asyncio
async def test_hotel_node_resolves_area_but_keeps_results_under_city_iata():
    mcp = AreaMcp()
    state = {"date_from": "2026-08-18", "date_to": "2026-08-25", "adults": 2,
             "accommodation_type": "hotel", "accommodation_area": "Trastevere",
             "destinations": [{"iata": "ROM", "name": "Roma"}]}
    out = await hotel_node(state, mcp=mcp)

    resolve_calls = [c for c in mcp.calls if c[0].endswith("resolve_destination_id")]
    search_calls = [c for c in mcp.calls if c[0].endswith("search_only_hotel")]
    assert resolve_calls == [("lastminute__resolve_destination_id",
                              {"lang": "it", "city_name": "Trastevere, Roma"})]
    assert len(search_calls) == 1
    assert search_calls[0][1]["destination"] == "778899"
    # The optimizer joins hotels to city flights by the original destination key.
    assert out["hotels"]["ROM"][0]["name"] == "Stay"


@pytest.mark.asyncio
async def test_hotel_node_unresolved_area_filters_city_results_using_property_details():
    mcp = AreaMcp(resolved=False)
    state = {"date_from": "2026-08-18", "date_to": "2026-08-25", "adults": 2,
             "accommodation_type": "home", "accommodation_area": "Trastevere",
             "destinations": [{"iata": "ROM", "name": "Roma"}]}
    out = await hotel_node(state, mcp=mcp)
    search = next(c for c in mcp.calls if c[0].endswith("search_only_hotel"))
    assert search[1]["destination"] == "131028"
    assert search[1]["max_results"] == 20
    assert search[1]["accommodation_type"] == "3,6,7,9,14"
    detail = next(c for c in mcp.calls if c[0].endswith("select_hotel_options"))
    assert detail[1]["hotel_internal_id"] == 7
    assert [item["name"] for item in out["hotels"]["ROM"]] == ["Stay"]


@pytest.mark.asyncio
async def test_hotel_node_never_returns_generic_city_results_for_unmatched_area():
    mcp = AreaMcp(resolved=False, detail_matches=False)
    state = {"date_from": "2026-08-18", "date_to": "2026-08-25", "adults": 2,
             "accommodation_type": "hotel", "accommodation_area": "Trastevere",
             "destinations": [{"iata": "ROM", "name": "Roma"}]}
    out = await hotel_node(state, mcp=mcp)
    assert out["hotels"]["ROM"] == []
