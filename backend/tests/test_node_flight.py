import json, pytest
from app.agent.nodes.flight import flight_node, normalize_flights


def test_normalize_flights_parses_price():
    raw = json.dumps([{"price_cents": 12000, "carrier": "Vueling", "pricing_id": "p1",
                       "summary": "MXP→TFS 1 scalo"}])
    res = normalize_flights(raw)
    assert res[0]["price_per_person"] == 120.0
    assert res[0]["pricing_id"] == "p1"
    assert res[0]["currency"] == "EUR"  # legacy payloads without currency remain EUR


def test_normalize_flights_real_schema_total_divided_by_adults():
    raw = json.dumps({"success": True, "currency": "EUR", "flights": [
        {"airline": "Ryanair", "outbound": "MXP 15:50 → TFS 19:25", "return": "TFS → MXP",
         "price": "1217.22 €", "price_amount": 121722, "carrier_id": "FR"}]})
    res = normalize_flights(raw, adults=3)
    assert res[0]["price_per_person"] == 405.74  # 1217.22 total / 3
    assert res[0]["airline"] == "Ryanair"
    assert res[0]["currency"] == "EUR"


def test_normalize_flights_keeps_only_eur_with_item_overriding_top_level():
    top_gbp = json.dumps({"currency": "GBP", "flights": [
        {"airline": "Wrong", "price_amount": 1000},
        {"airline": "EUR override", "currency": "eur", "price_amount": 2000},
    ]})
    assert [f["airline"] for f in normalize_flights(top_gbp)] == ["EUR override"]

    top_eur = json.dumps({"currency": "EUR", "flights": [
        {"airline": "GBP override", "currency": "GBP", "price_amount": 1000},
        {"airline": "EUR inherited", "price_amount": 2000},
    ]})
    result = normalize_flights(top_eur)
    assert [f["airline"] for f in result] == ["EUR inherited"]
    assert result[0]["currency"] == "EUR"


def test_normalize_flights_tags_departure_iata():
    raw = json.dumps([{"price_cents": 12000, "carrier": "Vueling", "pricing_id": "p1",
                       "summary": "MXP→TFS"}])
    res = normalize_flights(raw, departure_iata="LIN")
    assert res[0]["departure_iata"] == "LIN"


def test_normalize_flights_keeps_deeplink():
    raw = json.dumps({"flights": [{"price_amount": 82838, "carrier_id": "FR",
                                   "outbound": "MXP→TFS", "deeplink": "https://www.lastminute.ie/msr/route/x"}]})
    res = normalize_flights(raw, adults=2)
    assert res[0]["deeplink"] == "https://www.lastminute.ie/msr/route/x"


class FakeMcp:
    def __init__(self, result): self.result = result; self.calls = []
    async def call_tool(self, name, args): self.calls.append((name, args)); return self.result


class PerOriginMcp:
    """Returns a different price depending on the requested departure airport."""
    def __init__(self, prices): self.prices = prices; self.calls = []

    async def call_tool(self, name, args):
        self.calls.append((name, args))
        dep = args["departure"]
        return json.dumps({"flights": [{"airline": "X", "outbound": f"{dep}→{args['arrival']}",
                                        "price_amount": self.prices[dep]}]})


@pytest.mark.asyncio
async def test_flight_node_calls_mcp_per_destination():
    real = json.dumps({"flights": [{"airline": "Ryanair", "outbound": "MXP→TFS",
                                     "price_amount": 121722}]})
    mcp = FakeMcp(real)
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-18", "date_to": "2026-08-25",
             "adults": 3, "destinations": [{"iata": "TFS"}, {"iata": "LPA"}]}
    out = await flight_node(state, mcp=mcp)
    assert set(out["flights"].keys()) == {"TFS", "LPA"}
    assert out["flights"]["TFS"][0]["price_per_person"] == 405.74
    assert out["flights"]["TFS"][0]["departure_iata"] == "MXP"
    assert mcp.calls[0][0].endswith("search_flights")
    assert mcp.calls[0][1]["arrival"] == "TFS" and mcp.calls[0][1]["departure"] == "MXP"
    assert mcp.calls[0][1]["language"] == "it"


@pytest.mark.asyncio
async def test_flight_node_ignores_accommodation_area_and_keeps_city_iata():
    mcp = FakeMcp(json.dumps({"flights": [
        {"airline": "ITA", "outbound": "MXP→ROM", "price_amount": 20000},
    ]}))
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-18", "date_to": "2026-08-25",
             "adults": 1, "accommodation_area": "Trastevere",
             "destinations": [{"iata": "ROM", "name": "Roma"}]}
    await flight_node(state, mcp=mcp)
    assert len(mcp.calls) == 1
    assert mcp.calls[0][1]["arrival"] == "ROM"


@pytest.mark.asyncio
async def test_flight_node_searches_every_origin_and_tags_departure():
    # Cheaper from BGY than MXP for a single (dest, slot).
    mcp = PerOriginMcp({"MXP": 30000, "BGY": 20000})
    state = {"origin_iata": ["MXP", "BGY"], "date_from": "2026-08-18", "date_to": "2026-08-25",
             "adults": 1, "destinations": [{"iata": "TFS"}]}
    out = await flight_node(state, mcp=mcp)
    offers = out["flights"]["TFS"]
    # Kept offers from BOTH origins (one MCP call per (origin, slot) = 2 calls, 1 slot).
    assert len(mcp.calls) == 2
    assert {o["departure_iata"] for o in offers} == {"MXP", "BGY"}
    cheapest = min(offers, key=lambda o: o["price_per_person"])
    assert cheapest["departure_iata"] == "BGY"
    assert cheapest["price_per_person"] == 200.0
