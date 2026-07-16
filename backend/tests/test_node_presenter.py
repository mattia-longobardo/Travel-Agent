import asyncio
import json
import pytest
from app.agent.nodes.presenter import presenter_node
from app.agent.links import HOTEL_FALLBACK_URL, FLIGHT_FALLBACK_URL, PACKAGE_FALLBACK_URL

class StubLLM:
    async def complete_text(self, system, user): return "Ecco le mie proposte entro budget."


class RecordingLLM:
    """Captures the system + user payload handed to the concierge LLM."""
    def __init__(self): self.system = None; self.user = None
    async def complete_text(self, system, user):
        self.system = system; self.user = user
        return "Riassunto generato."


class ChainMcp:
    """Mimics the real lastminute flow: select_hotel_options mints a pricing_id + room rate,
    then generate_booking_link returns the checkout URL."""
    def __init__(self): self.calls = []
    async def call_tool(self, name, args):
        self.calls.append((name, args))
        if name.endswith("select_hotel_options"):
            return json.dumps({"pricing_id": "PID-1", "search_id": args["search_id"],
                               "room_options": [{"rate_id": "RID-9"}]})
        if name.endswith("generate_booking_link"):
            assert args == {"pricing_id": "PID-1", "rate_id": "RID-9"}
            return json.dumps({"success": True, "booking_url": "https://www.lastminute.com/s/tsx/7?vcSearchId=1"})
        return "[]"


class ExactPackageMcp:
    def __init__(self, select_payload):
        self.select_payload = select_payload
        self.calls = []

    async def call_tool(self, name, args):
        self.calls.append((name, args))
        if name.endswith("select_hotel_options"):
            return json.dumps(self.select_payload)
        if name.endswith("generate_booking_link"):
            return json.dumps({"booking_url": "https://www.lastminute.com/s/tsx/336937?checkout=1"})
        raise AssertionError(f"unexpected tool: {name}")


@pytest.mark.asyncio
async def test_presenter_no_results_gives_sensible_message():
    """When nothing was found, the message must explain it and not ask the user to paste options."""
    out = await presenter_node({"budget_per_person": 900, "ranked": []}, StubLLM(), mcp=None)
    msg = out["final_message"].lower()
    assert "non ho trovato" in msg
    assert "incoll" not in msg and "elenco" not in msg
    assert out["ranked"] == []


@pytest.mark.asyncio
async def test_presenter_empty_message_never_blames_budget():
    """Bugs 2/3: empty-results message must not contain '€' or a budget figure, and must be
    date/destination-oriented."""
    out = await presenter_node({"budget_per_person": 1800, "ranked": []}, StubLLM(), mcp=None)
    msg = out["final_message"]
    assert "€" not in msg
    assert "1800" not in msg
    assert "budget" not in msg.lower()
    low = msg.lower()
    assert "date" in low and "destinazione" in low


@pytest.mark.asyncio
async def test_presenter_empty_area_message_names_requested_area():
    out = await presenter_node({"ranked": [], "accommodation_area": "Trastevere"}, StubLLM())
    assert "Trastevere" in out["final_message"]
    assert "altra zona" in out["final_message"]


@pytest.mark.asyncio
async def test_presenter_grounds_llm_payload_when_cards_exist():
    """Bugs 2/3: with non-empty ranked, the presenter must NOT route into the empty-message
    branch, must return the LLM summary, and must hand the LLM concrete grounding (cheapest
    price, card count) so it can never hallucinate 'no solutions'."""
    state = {"budget_per_person": 750, "adults": 2, "ranked": [
        {"id": "pkg-1", "kind": "package", "destination": "Tenerife (TFS)", "price_per_person": 350,
         "price_total": 700, "currency": "EUR", "nights": 7, "hotel_name": "Hp", "hotel_stars": 4,
         "hotel_rating": 8.8, "flight_summary": "vp", "badge": "cheapest", "reason": "", "unmet": [],
         "flight_pp": None, "hotel_pp": None, "_pricing_id": "p", "_rate_id": "r"},
        {"id": "pkg-2", "kind": "package", "destination": "Gran Canaria (LPA)", "price_per_person": 600,
         "price_total": 1200, "currency": "EUR", "nights": 7, "hotel_name": "Hb", "hotel_stars": 5,
         "hotel_rating": 9.2, "flight_summary": "vp2", "badge": "best_value", "reason": "", "unmet": [],
         "flight_pp": None, "hotel_pp": None, "_pricing_id": "p2", "_rate_id": "r2"}]}
    llm = RecordingLLM()
    out = await presenter_node(state, llm, mcp=None)
    assert out["final_message"] == "Riassunto generato."
    assert len(out["ranked"]) == 2
    # grounding facts present in the user payload
    assert "350" in llm.user           # cheapest price
    assert "2" in llm.user             # card count
    # never frames the budget as a blocker when nothing exceeds it
    assert "no solution" not in llm.user.lower()


@pytest.mark.asyncio
async def test_presenter_summary_path_with_mixed_budget():
    """A mix of in-budget and over-budget cards still uses the summary path (not the empty path)
    and tells the LLM how many cards exceed the budget."""
    state = {"budget_per_person": 500, "adults": 1, "ranked": [
        {"id": "pkg-1", "kind": "package", "destination": "Tenerife (TFS)", "price_per_person": 300,
         "price_total": 300, "currency": "EUR", "nights": 7, "hotel_name": "Hp", "hotel_stars": 4,
         "hotel_rating": 8.8, "flight_summary": "vp", "badge": "cheapest", "reason": "", "unmet": [],
         "flight_pp": None, "hotel_pp": None, "_pricing_id": "p", "_rate_id": "r"},
        {"id": "pkg-2", "kind": "package", "destination": "Gran Canaria (LPA)", "price_per_person": 900,
         "price_total": 900, "currency": "EUR", "nights": 7, "hotel_name": "Hb", "hotel_stars": 5,
         "hotel_rating": 9.2, "flight_summary": "vp2", "badge": None, "reason": "",
         "unmet": ["Supera il budget di 400€ a persona"],
         "flight_pp": None, "hotel_pp": None, "_pricing_id": "p2", "_rate_id": "r2"}]}
    llm = RecordingLLM()
    out = await presenter_node(state, llm, mcp=None)
    assert out["final_message"] == "Riassunto generato."
    assert len(out["ranked"]) == 2
    # exactly one card over budget is communicated to the LLM
    assert "1" in llm.user

@pytest.mark.asyncio
async def test_presenter_sets_message_and_keeps_cards():
    state = {"budget_per_person": 750, "ranked": [
        {"id": "pkg-1", "kind": "package", "destination": "Tenerife (TFS)", "price_per_person": 350,
         "price_total": 700, "currency": "EUR", "nights": 7, "hotel_name": "Hp", "hotel_stars": 4,
         "hotel_rating": 8.8, "flight_summary": "vp", "badge": "cheapest", "reason": "",
         "_pricing_id": "p", "_rate_id": "r"}]}
    out = await presenter_node(state, StubLLM(), mcp=None)
    assert out["final_message"].startswith("Ecco")
    card = out["ranked"][0]
    assert card["reason"]               # popolata
    assert "booking_url" in card        # presente (anche se None)
    assert "_pricing_id" not in card    # campi interni rimossi


@pytest.mark.asyncio
async def test_presenter_mints_real_booking_url_via_chain():
    """A card with search_id + hotel id resolves to the real lastminute checkout URL."""
    state = {"adults": 2, "ranked": [
        {"id": "pkg-1", "kind": "separate", "destination": "Tenerife (TFS)", "price_per_person": 390,
         "currency": "EUR", "nights": 7, "date_from": "2026-08-18", "date_to": "2026-08-25",
         "badge": "cheapest", "reason": "",
         "_search_id": 616020433, "_hotel_internal_id": 7, "_flight_deeplink": "https://www.lastminute.ie/flight"}]}
    mcp = ChainMcp()
    out = await presenter_node(state, StubLLM(), mcp=mcp)
    card = out["ranked"][0]
    assert card["booking_url"] == "https://www.it.lastminute.com/s/tsx/7?vcSearchId=1"
    assert [c[0].split("__")[-1] for c in mcp.calls] == ["select_hotel_options", "generate_booking_link"]
    assert "_search_id" not in card and "_flight_deeplink" not in card


@pytest.mark.asyncio
async def test_presenter_separate_card_exposes_hotel_and_flight_urls():
    """Bug 5: a separate card mints a real HOTEL checkout link (hotel_url) and carries the
    flight deeplink (flight_url); booking_url = hotel_url. Package cards keep their combined
    booking_url with flight_url/hotel_url == None."""
    state = {"adults": 2, "ranked": [
        {"id": "pkg-1", "kind": "separate", "destination": "Tenerife (TFS)", "price_per_person": 390,
         "currency": "EUR", "nights": 7, "date_from": "2026-08-18", "date_to": "2026-08-25",
         "badge": "cheapest", "reason": "", "flight_pp": 90, "hotel_pp": 300,
         "_search_id": 616020433, "_hotel_internal_id": 7,
         "_flight_deeplink": "https://www.lastminute.ie/flight"},
        {"id": "pkg-2", "kind": "package", "destination": "Gran Canaria (LPA)", "price_per_person": 500,
         "currency": "EUR", "nights": 7, "date_from": "2026-08-18", "date_to": "2026-08-25",
         "badge": None, "reason": "", "flight_pp": None, "hotel_pp": None,
         "_pricing_id": "PID-1", "_rate_id": "RID-9"}]}
    mcp = ChainMcp()
    out = await presenter_node(state, StubLLM(), mcp=mcp)
    sep = out["ranked"][0]
    pkg = out["ranked"][1]
    assert sep["hotel_url"] == "https://www.it.lastminute.com/s/tsx/7?vcSearchId=1"
    assert sep["flight_url"] == "https://www.it.lastminute.com/flight"
    assert sep["booking_url"] == sep["hotel_url"]
    assert sep["property_url"].startswith("/stays/7?search_id=616020433")
    assert sep["property_url"] != sep["hotel_url"]
    assert sep["review_url"].startswith("https://www.it.lastminute.com/s/tsx/7?pageType=review")
    assert sep["flight_pp"] == 90 and sep["hotel_pp"] == 300
    # package card: real combined checkout, no separate urls
    assert pkg["booking_url"] == "https://www.it.lastminute.com/s/tsx/7?vcSearchId=1"
    assert pkg["flight_url"] is None and pkg["hotel_url"] is None


@pytest.mark.asyncio
async def test_presenter_tolerates_non_numeric_budget():
    class LLM:
        async def complete_text(self, s, u): return "ok"
    state = {"budget_per_person": "quel che serve", "adults": 1,
             "ranked": [{"price_per_person": 250, "destination": "Tenerife (TFS)",
                         "hotel_rating": 9, "date_from": "2026-12-04", "date_to": "2026-12-14",
                         "unmet": []}]}
    out = await presenter_node(state, LLM(), mcp=None)
    assert out["final_message"]


@pytest.mark.asyncio
async def test_presenter_hotel_only_card_has_no_flight_url():
    """Imp2: a hotel_only ranked card renders cleanly (flight_url None), no crash; its fallback
    booking link lands on the lastminute HOTELS section (never Google)."""
    state = {"adults": 1, "ranked": [
        {"id": "pkg-1", "kind": "hotel_only", "destination": "Abu Dhabi (AUH)",
         "price_per_person": 300, "currency": "EUR", "nights": 7,
         "date_from": "2026-12-04", "date_to": "2026-12-14",
         "flight_pp": None, "hotel_pp": 300, "badge": "cheapest", "reason": ""}]}
    out = await presenter_node(state, StubLLM(), mcp=None)
    card = out["ranked"][0]
    assert card["flight_url"] is None
    assert card["booking_url"] == HOTEL_FALLBACK_URL


@pytest.mark.asyncio
async def test_presenter_separate_hotel_button_never_points_to_flight():
    """The reported bug: when the hotel checkout can't be minted, the HOTEL button (hotel_url,
    and the booking_url that backs it) must fall back to the lastminute hotels section — NOT to
    the flight deeplink. flight_url keeps the flight; hotel_url/booking_url must differ from it."""
    flight = "https://www.lastminute.ie/flight?x=1"
    state = {"adults": 2, "ranked": [
        {"id": "pkg-1", "kind": "separate", "destination": "Tenerife (TFS)", "price_per_person": 390,
         "currency": "EUR", "nights": 7, "date_from": "2026-08-18", "date_to": "2026-08-25",
         "badge": None, "reason": "", "_flight_deeplink": flight}]}
    out = await presenter_node(state, StubLLM(), mcp=None)
    card = out["ranked"][0]
    assert card["flight_url"] == "https://www.it.lastminute.com/flight?x=1"
    assert card["hotel_url"] == HOTEL_FALLBACK_URL
    assert card["booking_url"] == HOTEL_FALLBACK_URL
    assert card["booking_url"] != flight and card["hotel_url"] != flight


@pytest.mark.asyncio
async def test_presenter_separate_without_flight_deeplink_uses_flight_section():
    """A separate card with no flight deeplink still gives the flight button a working target
    (the lastminute flights section), never None."""
    state = {"adults": 2, "ranked": [
        {"id": "pkg-1", "kind": "separate", "destination": "Tenerife (TFS)", "price_per_person": 390,
         "currency": "EUR", "nights": 7, "date_from": "2026-08-18", "date_to": "2026-08-25",
         "badge": None, "reason": ""}]}
    out = await presenter_node(state, StubLLM(), mcp=None)
    card = out["ranked"][0]
    assert card["flight_url"] == FLIGHT_FALLBACK_URL
    assert card["hotel_url"] == HOTEL_FALLBACK_URL


@pytest.mark.asyncio
async def test_presenter_mints_real_url_for_every_card_not_just_top_n():
    """The deeplink must be attempted for ALL cards, not only the first batch: every package
    card with resolvable ids resolves to the real lastminute checkout, even beyond the 12th."""
    ranked = [
        {"id": f"pkg-{i}", "kind": "package", "destination": f"Dest {i} (D{i})",
         "price_per_person": 300 + i, "currency": "EUR", "nights": 7,
         "date_from": "2026-08-18", "date_to": "2026-08-25", "badge": None, "reason": "",
         "_pricing_id": "PID-1", "_rate_id": "RID-9"}
        for i in range(25)]
    out = await presenter_node({"adults": 2, "ranked": ranked}, StubLLM(), mcp=ChainMcp())
    assert len(out["ranked"]) == 25
    assert all(c["booking_url"] == "https://www.it.lastminute.com/s/tsx/7?vcSearchId=1"
               for c in out["ranked"]), "every card should get the minted checkout URL"


@pytest.mark.asyncio
async def test_presenter_card_has_review_url_from_ids():
    """Task 3: a card carrying _hotel_internal_id + _search_id (+ dates/dest) exposes a non-stripped
    review_url = the verified lastminute /s/tsx/… page, while the internal ids are stripped."""
    state = {"adults": 2, "ranked": [
        {"id": "p1", "kind": "package", "destination": "Tenerife (TFS)", "price_per_person": 300,
         "currency": "EUR", "nights": 4, "date_from": "2026-07-26", "date_to": "2026-07-30",
         "badge": None, "reason": "", "hotel_name": "Sea",
         "_pricing_id": "PID-1", "_rate_id": "RID-9",
         "_search_id": 768510350, "_hotel_internal_id": 336937, "_lm_dest_code": "TCI"}]}
    out = await presenter_node(state, StubLLM(), mcp=ChainMcp())
    card = out["ranked"][0]
    assert card["review_url"] == ("https://www.it.lastminute.com/s/tsx/336937?pageType=review"
        "&destination=TCI&dateFrom=2026-07-26&dateTo=2026-07-30&adults=2&vcSearchId=768510350&searchMode=HO")
    assert card["property_url"].startswith(
        "/stays/336937?search_id=768510350&date_from=2026-07-26&date_to=2026-07-30&kind=hotel"
    )
    assert "name=Sea" in card["property_url"]
    assert card["property_url"] != card["booking_url"]
    assert "_search_id" not in card  # internal ids stripped


@pytest.mark.asyncio
async def test_presenter_never_uses_checkout_as_property_url_without_identity():
    state = {"adults": 1, "ranked": [{
        "id": "p1", "kind": "package", "destination": "Roma (FCO)",
        "price_per_person": 250, "date_from": "2026-08-01", "date_to": "2026-08-04",
        "badge": None, "reason": "", "hotel_name": "Stay",
        "_pricing_id": "PID-1", "_rate_id": "RID-9",
    }]}
    out = await presenter_node(state, StubLLM(), mcp=ChainMcp())
    card = out["ranked"][0]
    assert card["booking_url"]
    assert card["property_url"] is None
    assert card["review_url"] is None


@pytest.mark.asyncio
async def test_presenter_fallback_uses_review_url_when_mint_fails(monkeypatch):
    """Task 3: when minting fails (hung MCP) but the card carries ids, the booking_url falls back
    to the constructed review URL — not the bare section page / homepage."""
    import app.agent.nodes.presenter as presenter
    monkeypatch.setattr(presenter, "_MINT_TIMEOUT", 0.05)

    class HangingMcp:
        async def call_tool(self, n, a):
            await asyncio.sleep(1.0)
            return "[]"

    state = {"adults": 2, "ranked": [
        {"id": "p1", "kind": "package", "destination": "Tenerife (TFS)", "price_per_person": 300,
         "currency": "EUR", "nights": 4, "date_from": "2026-07-26", "date_to": "2026-07-30",
         "badge": None, "reason": "", "_pricing_id": "X", "_rate_id": "Y",
         "_search_id": 768510350, "_hotel_internal_id": 336937, "_lm_dest_code": "TCI"}]}
    out = await presenter_node(state, StubLLM(), mcp=HangingMcp())
    assert out["ranked"][0]["booking_url"].startswith("https://www.it.lastminute.com/s/tsx/336937?")


@pytest.mark.asyncio
async def test_presenter_mint_timeout_falls_back_to_lastminute(monkeypatch):
    """A hung MCP call counts as a failed mint: it must fall back to the lastminute section URL
    (not Google, and without blocking the whole response)."""
    import app.agent.nodes.presenter as presenter
    monkeypatch.setattr(presenter, "_MINT_TIMEOUT", 0.05)

    class HangingMcp:
        async def call_tool(self, name, args):
            await asyncio.sleep(1.0)
            return "[]"

    state = {"adults": 2, "ranked": [
        {"id": "pkg-1", "kind": "package", "destination": "Tenerife (TFS)", "price_per_person": 390,
         "currency": "EUR", "nights": 7, "date_from": "2026-08-18", "date_to": "2026-08-25",
         "badge": None, "reason": "", "_pricing_id": "PID-1", "_rate_id": "RID-9"}]}
    out = await presenter_node(state, StubLLM(), mcp=HangingMcp())
    assert out["ranked"][0]["booking_url"] == PACKAGE_FALLBACK_URL


@pytest.mark.asyncio
async def test_presenter_flight_only_uses_deeplink_and_skips_minting():
    """flight_only cards book via the flight deeplink (fallback: flights section) with no
    hotel links and no select/generate MCP round-trips."""
    from app.agent.links import FLIGHT_FALLBACK_URL
    mcp = ChainMcp()
    ranked = [
        {"id": "pkg-1", "kind": "flight_only", "destination": "Atene (ATH)",
         "dest_iata": "ATH", "dest_name": "Atene", "price_per_person": 95.0,
         "flight_summary": "MXP→ATH", "hotel_rating": None, "unmet": [], "badge": None,
         "currency": "EUR", "nights": 7, "date_from": "2026-08-01", "date_to": "2026-08-08",
         "_flight_deeplink": "https://www.lastminute.com/volo/123",
         "_pricing_id": None, "_rate_id": None, "_search_id": None,
         "_hotel_internal_id": None, "_lm_dest_code": None},
        {"id": "pkg-2", "kind": "flight_only", "destination": "Atene (ATH)",
         "dest_iata": "ATH", "dest_name": "Atene", "price_per_person": 120.0,
         "flight_summary": "MXP→ATH bis", "hotel_rating": None, "unmet": [], "badge": None,
         "currency": "EUR", "nights": 7, "date_from": "2026-08-01", "date_to": "2026-08-08",
         "_flight_deeplink": None,
         "_pricing_id": None, "_rate_id": None, "_search_id": None,
         "_hotel_internal_id": None, "_lm_dest_code": None},
    ]
    out = await presenter_node({"ranked": ranked, "adults": 1}, StubLLM(), mcp)
    cards = out["ranked"]
    assert cards[0]["booking_url"] == "https://www.it.lastminute.com/volo/123"
    assert cards[0]["flight_url"] == "https://www.it.lastminute.com/volo/123"
    assert cards[0]["hotel_url"] is None and cards[0]["review_url"] is None
    assert cards[1]["booking_url"] == FLIGHT_FALLBACK_URL
    assert mcp.calls == []  # no hotel minting for flight-only cards


@pytest.mark.asyncio
@pytest.mark.parametrize("initial_summary", [
    "Orari non disponibili · Compagnia EasyJet",
    "Partenza 17:25 → durata 03:40",
    "17:25 → 21:05",
])
@pytest.mark.parametrize("select_payload", [
    [{
        "pricing_id": "PID-EXACT",
        "room_options": [{"rate_id": "RID-EXACT"}],
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
    }],
    {
        "pricing_id": "PID-EXACT",
        "room_options": [{"rate_id": "RID-EXACT"}],
        "outbound": {
            "from": "MXP", "to": "TFS",
            "departure_time": "2026-09-05T17:25:00+02:00",
            "arrival_time": "2026-09-05T21:05:00+01:00",
        },
        "return": {
            "from": "TFS", "to": "MXP",
            "departure_time": "2026-09-12T21:50:00+01:00",
            "arrival_time": "2026-09-13T03:05:00+02:00",
        },
    },
])
async def test_presenter_enriches_package_times_only_from_exact_selection(select_payload, initial_summary):
    mcp = ExactPackageMcp(select_payload)
    state = {"adults": 2, "ranked": [{
        "id": "pkg-1", "kind": "package", "destination": "Tenerife (TFS)",
        "price_per_person": 700, "price_total": 1400, "currency": "EUR", "nights": 7,
        "date_from": "2026-09-05", "date_to": "2026-09-12",
        "hotel_name": "Exact Hotel", "flight_summary": initial_summary,
        "badge": None, "reason": "", "unmet": [],
        "_flight_carrier": "EasyJet", "_search_id": 543500301,
        "_hotel_internal_id": 336937,
    }]}
    card = (await presenter_node(state, StubLLM(), mcp=mcp))["ranked"][0]
    assert "A: MXP 05/09 17:25 → TFS 05/09 21:05" in card["flight_summary"]
    assert "R: TFS 12/09 21:50 → MXP 13/09 03:05" in card["flight_summary"]
    assert mcp.calls[0] == (
        "lastminute__select_hotel_options",
        {"search_id": 543500301, "hotel_internal_id": 336937,
         "date_from": "2026-09-05", "date_to": "2026-09-12"},
    )
    assert all("search_flight" not in name for name, _ in mcp.calls)


@pytest.mark.asyncio
async def test_presenter_package_uses_explicit_carrier_fallback_when_exact_times_absent():
    state = {"ranked": [{
        "id": "pkg-1", "kind": "package", "destination": "Tenerife (TFS)",
        "price_per_person": 700, "flight_summary": "EasyJet", "_flight_carrier": "EasyJet",
        "badge": None, "reason": "", "unmet": [],
    }]}
    card = (await presenter_node(state, StubLLM(), mcp=None))["ranked"][0]
    assert card["flight_summary"] == "Orari non disponibili · Compagnia EasyJet"


@pytest.mark.asyncio
async def test_presenter_keeps_exact_flight_times_when_link_generation_times_out(monkeypatch):
    import app.agent.nodes.presenter as presenter
    monkeypatch.setattr(presenter, "_MINT_TIMEOUT", 0.05)

    class SlowGenerateMcp:
        async def call_tool(self, name, args):
            if name.endswith("select_hotel_options"):
                return json.dumps({
                    "pricing_id": "PID",
                    "room_options": [{"rate_id": "RID"}],
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
                })
            if name.endswith("generate_booking_link"):
                await asyncio.sleep(1)
            return "[]"

    state = {"adults": 2, "ranked": [{
        "id": "pkg-1", "kind": "package", "destination": "Tenerife (TFS)",
        "price_per_person": 700, "date_from": "2026-09-05", "date_to": "2026-09-12",
        "flight_summary": "Orari non disponibili · Compagnia EasyJet",
        "badge": None, "reason": "", "unmet": [],
        "_search_id": 543500301, "_hotel_internal_id": 336937,
    }]}
    card = (await presenter_node(state, StubLLM(), SlowGenerateMcp()))["ranked"][0]
    assert "17:25" in card["flight_summary"] and "21:05" in card["flight_summary"]
    # Checkout generation timed out: the URL falls back safely, while exact flight data survives.
    assert card["booking_url"].startswith("https://www.it.lastminute.com/s/tsx/336937?")
