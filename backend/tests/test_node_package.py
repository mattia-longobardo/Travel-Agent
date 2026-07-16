import json, pytest
from app.agent.nodes.package import (
    flight_details_summary,
    flight_summary_has_times,
    normalize_packages,
    package_node,
)


def test_normalize_packages_computes_per_person():
    raw = json.dumps([{"total_price": 1380, "adults": 2, "hotel": {"name": "X", "stars": 4, "rating": 8.6},
                       "flight": {"summary": "MXP→TFS"}, "pricing_id": "pp", "rate_id": "rr"}])
    res = normalize_packages(raw, adults=2)
    assert res[0]["price_per_person"] == 690.0
    assert res[0]["price_total"] == 1380.0
    assert res[0]["hotel_stars"] == 4 and res[0]["rate_id"] == "rr"
    assert res[0]["currency"] == "EUR"  # legacy payloads without currency remain EUR


def test_normalize_packages_real_schema():
    raw = json.dumps({"products_summary": [
        {"internal_id_hotel": 1, "name": "Alua Tenerife", "stars": 4, "rating": 87,
         "reviews": 835, "distance_km": 2.3, "facilities": ["Piscina", "Spa"],
         "cancellable": True,
         "price_total": 2481.39, "currency": "EUR", "carrier": "Ryanair"}]})
    res = normalize_packages(raw, adults=3)
    assert res[0]["price_per_person"] == round(2481.39 / 3, 2)
    assert res[0]["hotel_name"] == "Alua Tenerife" and res[0]["hotel_stars"] == 4
    assert res[0]["flight_summary"] == "Orari non disponibili · Compagnia Ryanair"
    assert res[0]["currency"] == "EUR"
    assert res[0]["hotel_reviews"] == 835
    assert res[0]["hotel_distance_km"] == 2.3
    assert res[0]["hotel_facilities"] == ["Piscina", "Spa"]
    assert res[0]["hotel_cancellable"] is True


def test_normalize_packages_prefers_actual_outbound_and_return_times():
    raw = json.dumps({"products_summary": [{
        "internal_id_hotel": 1,
        "name": "Alua Tenerife",
        "price_total": 900,
        "carrier": "EasyJet",
        "flight_details": {
            "outbound": {
                "from": "MXP", "to": "TFS",
                "departure_time": "2026-09-05T17:25:00+02:00",
                "arrival_time": "2026-09-05T21:05:00+01:00",
            },
            "inbound": {
                "from": "TFS", "to": "MXP",
                "departure_time": "2026-09-12T21:50:00+01:00",
                "arrival_time": "2026-09-13T03:05:00+02:00",
            },
        },
    }]})
    summary = normalize_packages(raw)[0]["flight_summary"]
    assert "A: MXP 05/09 17:25 → TFS 05/09 21:05" in summary
    assert "R: TFS 12/09 21:50 → MXP 13/09 03:05" in summary
    assert flight_summary_has_times(summary)


def test_flight_summary_requires_both_departure_and_arrival_time():
    assert not flight_summary_has_times("Partenza MXP alle 17:25")
    assert flight_summary_has_times("MXP 17:25 → TFS 21:05")
    assert flight_summary_has_times("Partenza 17:25, arrivo 21:05")


@pytest.mark.parametrize("summary", [
    "Check-in 10:00 · durata 02:30",
    "Partenza 10:00 → durata 02:30",
    "Partenza 10:00 → partenza 12:00",
    "Partenze disponibili: 10:00 e 12:00",
    "10:00 → 12:00",
])
def test_flight_summary_rejects_generic_duration_or_two_departure_times(summary):
    assert not flight_summary_has_times(summary)


def test_structured_flight_does_not_join_two_partial_legs_into_a_complete_summary():
    assert flight_details_summary({
        "outbound": {
            "from": "MXP", "to": "TFS",
            "departure_time": "2026-09-05T17:25:00+02:00",
        },
        "inbound": {
            "from": "TFS", "to": "MXP",
            "arrival_time": "2026-09-13T03:05:00+02:00",
        },
    }) is None


def test_normalize_packages_keeps_only_eur_with_item_overriding_top_level():
    raw = json.dumps({"currency": "GBP", "products_summary": [
        {"internal_id_hotel": 1, "name": "GBP inherited", "price_total": 100},
        {"internal_id_hotel": 2, "name": "EUR item", "currency": "EUR", "price_total": 200},
    ]})
    result = normalize_packages(raw)
    assert [p["hotel_name"] for p in result] == ["EUR item"]
    assert result[0]["currency"] == "EUR"

    item_gbp = json.dumps({"currency": "EUR", "products_summary": [
        {"internal_id_hotel": 3, "name": "GBP item", "currency": "GBP", "price_total": 100},
    ]})
    assert normalize_packages(item_gbp) == []


def test_normalize_packages_captures_lm_dest_code():
    """lm_dest_code (search_params.destination) is the lastminute destination code, distinct
    from the airport IATA; needed to build the verified review URL."""
    raw = json.dumps({"search_id": 1, "search_params": {"destination": "TCI"},
                      "products_summary": [{"internal_id_hotel": 7, "name": "Sea",
                                            "stars": 4, "rating": 85, "price_total": 600.0}]})
    res = normalize_packages(raw, adults=2)
    assert res[0]["lm_dest_code"] == "TCI"


def test_normalize_packages_reads_item_and_nested_hotel_identity():
    raw = json.dumps({"products_summary": [{
        "price_total": 900, "name": "Package stay", "search_id": 123,
        "hotel": {"id": 456, "stars": 4, "rating": 88},
        "search_params": {"destination": "ROM"},
    }]})
    res = normalize_packages(raw)
    assert res[0]["search_id"] == 123
    assert res[0]["hotel_internal_id"] == 456
    assert res[0]["lm_dest_code"] == "ROM"
    assert res[0]["accommodation_kind"] == "hotel"


def test_normalize_packages_preserves_search_job_accommodation_kind():
    raw = json.dumps({"products_summary": [
        {"internal_id_hotel": 7, "name": "Villa", "price_total": 900},
    ]})
    assert normalize_packages(raw, accommodation_kind="home")[0]["accommodation_kind"] == "home"


class FakeMcp:
    def __init__(self, result): self.result = result; self.calls = []
    async def call_tool(self, name, args): self.calls.append((name, args)); return self.result


@pytest.mark.asyncio
async def test_package_node_per_destination_uses_eur_lang():
    real = json.dumps({"products_summary": [
        {"internal_id_hotel": 1, "name": "Combo", "stars": 4, "rating": 82, "price_total": 1200.0}]})
    mcp = FakeMcp(real)
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-18", "date_to": "2026-08-25",
             "adults": 2, "min_stars": 4, "destinations": [{"iata": "LPA"}]}
    out = await package_node(state, mcp=mcp)
    assert out["packages"]["LPA"][0]["price_per_person"] == 600.0
    assert mcp.calls[0][1]["lang"] == "it" and mcp.calls[0][1]["destination"] == "LPA"
    assert mcp.calls[0][1]["adults"] == "2"  # package tool requires adults as a string
    assert [c[1]["accommodation_type"] for c in mcp.calls] == ["1,2", "3,6,7,9,14"]
    assert {p["accommodation_kind"] for p in out["packages"]["LPA"]} == {"hotel", "home"}


@pytest.mark.asyncio
@pytest.mark.parametrize(("requested", "mcp_filter"), [
    ("hotel", "1,2"),
    ("home", "3,6,7,9,14"),
])
async def test_package_node_applies_requested_accommodation_filter(requested, mcp_filter):
    raw = json.dumps({"products_summary": [
        {"internal_id_hotel": 7, "name": "Stay", "price_total": 900},
    ]})
    mcp = FakeMcp(raw)
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-18", "date_to": "2026-08-25",
             "adults": 2, "accommodation_type": requested,
             "destinations": [{"iata": "LPA"}]}
    out = await package_node(state, mcp=mcp)
    assert len(mcp.calls) == 1
    assert mcp.calls[0][1]["accommodation_type"] == mcp_filter
    assert out["packages"]["LPA"][0]["accommodation_kind"] == requested


@pytest.mark.asyncio
async def test_package_node_skips_generic_city_packages_when_area_is_requested():
    mcp = FakeMcp("must not be called")
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-18", "date_to": "2026-08-25",
             "adults": 2, "accommodation_type": "both", "accommodation_area": "Trastevere",
             "destinations": [{"iata": "ROM", "name": "Roma"}]}
    out = await package_node(state, mcp=mcp)
    assert mcp.calls == []
    assert out["packages"] == {"ROM": []}
