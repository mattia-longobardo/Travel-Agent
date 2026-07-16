import pytest
from app.agent.nodes.optimizer import _unmet, combine_separate, optimizer_node


@pytest.mark.asyncio
async def test_optimizer_tolerates_non_numeric_budget():
    state = {
        "budget_per_person": "quel che serve",  # must not crash
        "destinations": [{"iata": "TFS", "name": "Tenerife"}],
        "flights": {"TFS": [{"price_per_person": 200, "date_from": "2026-12-04", "date_to": "2026-12-14"}]},
        "hotels": {"TFS": [{"price_per_person": 300, "rating": 9, "date_from": "2026-12-04", "date_to": "2026-12-14"}]},
        "packages": {}, "adults": 1, "currency": "EUR",
    }
    out = await optimizer_node(state)
    assert out["ranked"]
    assert out["ranked"][0]["unmet"] == []  # no budget => nothing unmet on price


@pytest.mark.asyncio
async def test_optimizer_hotel_only_when_no_flight():
    state = {"no_flight": True, "destinations": [{"iata": "TFS", "name": "Tenerife"}],
             "flights": {}, "packages": {},
             "hotels": {"TFS": [{"price_per_person": 300, "name": "Anantara", "stars": 5,
                                 "rating": 9, "date_from": "2026-12-04", "date_to": "2026-12-14"}]},
             "adults": 1, "currency": "EUR"}
    out = await optimizer_node(state)
    assert out["ranked"]
    c = out["ranked"][0]
    assert c["kind"] == "hotel_only"
    assert c["price_per_person"] == 300
    assert c["flight_pp"] is None


@pytest.mark.asyncio
async def test_optimizer_drops_non_eur_offers_and_forces_eur_card_currency():
    df, dt = "2026-08-01", "2026-08-08"
    state = {
        "search_mode": "flight_hotel", "currency": "GBP", "adults": 1,
        "budget_per_person": 1000, "destinations": [{"iata": "ROM", "name": "Roma"}],
        "flights": {"ROM": [
            {"price_per_person": 10, "currency": "GBP", "summary": "cheap wrong",
             "date_from": df, "date_to": dt},
            {"price_per_person": 100, "currency": "EUR", "summary": "valid",
             "date_from": df, "date_to": dt},
        ]},
        "hotels": {"ROM": [
            {"price_per_person": 200, "currency": "EUR", "name": "H", "hotel_internal_id": 1,
             "date_from": df, "date_to": dt},
        ]},
        "packages": {"ROM": [
            {"price_per_person": 1, "price_total": 1, "currency": "GBP", "hotel_name": "Wrong",
             "hotel_internal_id": 2, "date_from": df, "date_to": dt},
        ]},
    }
    ranked = (await optimizer_node(state))["ranked"]
    assert len(ranked) == 1
    assert ranked[0]["kind"] == "separate"
    assert ranked[0]["price_per_person"] == 300
    assert ranked[0]["flight_summary"] == "valid"
    assert ranked[0]["currency"] == "EUR"


@pytest.mark.asyncio
async def test_optimizer_legacy_missing_currency_is_eur_even_if_state_says_gbp():
    state = {
        "search_mode": "flight_only", "currency": "GBP", "adults": 1,
        "destinations": [{"iata": "ATH", "name": "Atene"}],
        "flights": {"ATH": [{"price_per_person": 99, "summary": "legacy"}]},
        "hotels": {}, "packages": {},
    }
    card = (await optimizer_node(state))["ranked"][0]
    assert card["currency"] == "EUR"

def test_combine_separate_sums_flight_and_hotel():
    c = combine_separate({"iata": "TFS", "name": "Tenerife"},
                         [{"price_per_person": 90, "summary": "s", "pricing_id": "f"}],
                         [{"price_per_person": 300, "name": "H", "stars": 4, "rating": 8.5,
                           "hotel_internal_id": 1}])
    assert c["price_per_person"] == 390
    assert c["kind"] == "separate"
    assert c["currency"] == "EUR"


def test_combine_separate_rejects_explicit_non_eur_side():
    dest = {"iata": "TFS", "name": "Tenerife"}
    assert combine_separate(
        dest,
        [{"price_per_person": 90, "currency": "GBP"}],
        [{"price_per_person": 300, "currency": "EUR", "name": "H"}],
    ) is None
    assert combine_separate(
        dest,
        [{"price_per_person": 90, "currency": "EUR"}],
        [{"price_per_person": 300, "currency": "USD", "name": "H"}],
    ) is None


def test_combine_separate_carries_cheapest_departure_iata():
    c = combine_separate({"iata": "TFS", "name": "Tenerife"},
                         [{"price_per_person": 120, "summary": "s", "pricing_id": "f1",
                           "departure_iata": "MXP"},
                          {"price_per_person": 90, "summary": "s", "pricing_id": "f2",
                           "departure_iata": "BGY"}],
                         [{"price_per_person": 300, "name": "H", "stars": 4, "rating": 8.5,
                           "hotel_internal_id": 1}])
    assert c["price_per_person"] == 390              # 90 (cheapest flight) + 300
    assert c["departure_iata"] == "BGY"              # origin of the chosen flight

def test_combine_separate_carries_price_breakdown():
    """Separate cards expose flight_pp + hotel_pp summing (±rounding) to price_per_person."""
    c = combine_separate({"iata": "TFS", "name": "Tenerife"},
                         [{"price_per_person": 90, "summary": "s", "pricing_id": "f"}],
                         [{"price_per_person": 300, "name": "H", "stars": 4, "rating": 8.5,
                           "hotel_internal_id": 1}])
    assert c["flight_pp"] == 90
    assert c["hotel_pp"] == 300
    assert round(c["flight_pp"] + c["hotel_pp"], 2) == c["price_per_person"]


def test_combine_separate_propagates_accommodation_kind():
    c = combine_separate(
        {"iata": "FCO", "name": "Roma"},
        [{"price_per_person": 90, "summary": "s"}],
        [{"price_per_person": 300, "name": "Casa", "rating": 8.5,
          "hotel_internal_id": 1, "accommodation_kind": "home"}],
    )
    assert c["accommodation_kind"] == "home"


def test_home_never_gets_hotel_star_warning_but_keeps_budget_warning():
    warnings = _unmet(
        {"kind": "hotel_only", "accommodation_kind": "home", "hotel_stars": None,
         "price_per_person": 700},
        budget=500,
        min_stars=4,
    )
    assert warnings == ["Supera il budget di 200€ a persona"]


def test_hotel_still_gets_star_warning():
    warnings = _unmet(
        {"kind": "hotel_only", "accommodation_kind": "hotel", "hotel_stars": 3,
         "price_per_person": 400},
        budget=500,
        min_stars=4,
    )
    assert warnings == ["Hotel 3★, sotto le 4★ richieste"]


def test_combine_separate_propagates_listing_features():
    c = combine_separate(
        {"iata": "TFS", "name": "Tenerife"},
        [{"price_per_person": 100, "summary": "MXP 10:00 → TFS 14:00"}],
        [{"price_per_person": 300, "name": "Stay", "hotel_internal_id": 7,
          "hotel_reviews": 412, "hotel_distance_km": 1.4,
          "hotel_facilities": ["Piscina", "Wi-Fi"], "hotel_cancellable": False}],
    )
    assert c["hotel_reviews"] == 412
    assert c["hotel_distance_km"] == 1.4
    assert c["hotel_facilities"] == ["Piscina", "Wi-Fi"]
    assert c["hotel_cancellable"] is False


@pytest.mark.asyncio
async def test_optimizer_separate_card_breakdown_and_package_nulls():
    """Separate cards carry flight_pp/hotel_pp; package cards carry them as None."""
    state = {"budget_per_person": 5000, "currency": "EUR", "adults": 1, "min_stars": None,
             "date_from": "2026-08-01", "date_to": "2026-08-08",
             "destinations": [{"iata": "TFS", "name": "Tenerife"}],
             "flights": {"TFS": [{"price_per_person": 90, "summary": "v", "pricing_id": "f1",
                                  "date_from": "2026-08-01", "date_to": "2026-08-08"}]},
             "hotels": {"TFS": [{"price_per_person": 300, "name": "H1", "stars": 4, "rating": 8.5,
                                 "hotel_internal_id": 1, "date_from": "2026-08-01", "date_to": "2026-08-08"}]},
             "packages": {"TFS": [{"price_per_person": 350, "price_total": 350, "hotel_name": "Hp",
                          "hotel_stars": 4, "hotel_rating": 8.8, "flight_summary": "vp",
                          "pricing_id": "p", "rate_id": "r",
                          "date_from": "2026-08-01", "date_to": "2026-08-08"}]}}
    out = await optimizer_node(state)
    ranked = out["ranked"]
    sep = next(c for c in ranked if c["kind"] == "separate")
    pkg = next(c for c in ranked if c["kind"] == "package")
    assert sep["flight_pp"] == 90 and sep["hotel_pp"] == 300
    assert round(sep["flight_pp"] + sep["hotel_pp"], 2) == sep["price_per_person"]
    assert pkg["flight_pp"] is None and pkg["hotel_pp"] is None
    assert sep["accommodation_kind"] == "hotel"
    assert pkg["accommodation_kind"] == "hotel"


@pytest.mark.asyncio
async def test_optimizer_ranks_cheapest_and_flags_over_budget():
    state = {"budget_per_person": 750, "currency": "EUR", "adults": 2, "min_stars": 4,
             "date_from": "2026-08-19", "date_to": "2026-08-26",
             "destinations": [{"iata": "TFS", "name": "Tenerife"}, {"iata": "LPA", "name": "Gran Canaria"}],
             "flights": {"TFS": [{"price_per_person": 90, "summary": "v1", "pricing_id": "f1"}],
                         "LPA": [{"price_per_person": 700, "summary": "v2", "pricing_id": "f2"}]},
             "hotels": {"TFS": [{"price_per_person": 300, "name": "H1", "stars": 4, "rating": 8.5, "hotel_internal_id": 1}],
                        "LPA": [{"price_per_person": 300, "name": "H2", "stars": 4, "rating": 9.0, "hotel_internal_id": 2}]},
             "packages": {"TFS": [{"price_per_person": 350, "price_total": 700, "hotel_name": "Hp",
                          "hotel_stars": 4, "hotel_rating": 8.8, "flight_summary": "vp", "pricing_id": "p", "rate_id": "r"}]}}
    out = await optimizer_node(state)
    ranked = out["ranked"]
    # One best card per destination: TFS best = package 350 (in budget); LPA best = 1000 (over budget).
    assert ranked[0]["price_per_person"] == 350 and ranked[0]["badge"] == "cheapest"
    assert ranked[0]["unmet"] == []
    lpa = next(o for o in ranked if "LPA" in o["destination"])
    # Over-budget options are no longer hidden — they are surfaced and flagged.
    assert lpa["price_per_person"] == 1000
    assert any("budget" in w.lower() for w in lpa["unmet"])


@pytest.mark.asyncio
async def test_optimizer_dedupes_same_hotel_to_cheapest_period():
    """Same hotel offered across 3 periods at different prices ⇒ exactly ONE card,
    the cheapest period (no per-period duplicates)."""
    slots = [("2026-08-01", "2026-08-08"), ("2026-08-08", "2026-08-15"),
             ("2026-08-15", "2026-08-22")]
    prices = [500, 300, 400]  # cheapest is the middle period (300)
    fl, ho = [], []
    for (df, dt), price in zip(slots, prices):
        fl.append({"price_per_person": price - 100, "summary": "v", "pricing_id": f"f-{df}",
                   "departure_iata": "MXP", "date_from": df, "date_to": dt})
        ho.append({"price_per_person": 100, "name": "Saradari Beach Hotel", "stars": 4,
                   "rating": 8.0, "hotel_internal_id": 7, "date_from": df, "date_to": dt})
    state = {"budget_per_person": 5000, "currency": "EUR", "adults": 1, "min_stars": None,
             "destinations": [{"iata": "TFS", "name": "Tenerife"}],
             "flights": {"TFS": fl}, "hotels": {"TFS": ho}, "packages": {}}
    out = await optimizer_node(state)
    ranked = out["ranked"]
    assert len(ranked) == 1                                   # not 3
    assert ranked[0]["price_per_person"] == 300              # cheapest period kept
    assert ranked[0]["date_from"] == "2026-08-08"


@pytest.mark.asyncio
async def test_optimizer_keeps_up_to_ten_distinct_hotels_with_dest_fields():
    """Two destinations, each with > 10 distinct hotels ⇒ each contributes at most 10 cards,
    cheapest first, carrying dest_iata / dest_name."""
    dests = [{"iata": "TFS", "name": "Tenerife"}, {"iata": "LPA", "name": "Gran Canaria"}]
    df, dt = "2026-08-01", "2026-08-08"
    flights, hotels = {}, {}
    for di, d in enumerate(dests):
        fl, ho = [], []
        for hi in range(15):  # 15 distinct hotels per dest
            fl.append({"price_per_person": 100, "summary": "v", "pricing_id": f"f{di}{hi}",
                       "departure_iata": "MXP", "date_from": df, "date_to": dt})
            ho.append({"price_per_person": 100 + hi, "name": f"Hotel-{di}-{hi}", "stars": 4,
                       "rating": 8.0, "hotel_internal_id": di * 100 + hi,
                       "date_from": df, "date_to": dt})
        flights[d["iata"]] = fl
        hotels[d["iata"]] = ho
    state = {"budget_per_person": 5000, "currency": "EUR", "adults": 1, "min_stars": None,
             "destinations": dests, "flights": flights, "hotels": hotels, "packages": {}}
    out = await optimizer_node(state)
    ranked = out["ranked"]
    for d in dests:
        cards = [c for c in ranked if c["dest_iata"] == d["iata"]]
        assert len(cards) == 10                               # capped at MAX_PER_DEST
        assert all(c["dest_name"] == d["name"] for c in cards)
        # cheapest 10 of the 15 distinct hotels (prices 100..109)
        assert max(c["price_per_person"] for c in cards) == 209
    assert len(ranked) == 20


@pytest.mark.asyncio
async def test_optimizer_surfaces_over_budget_with_unmet():
    """Two DISTINCT hotels: a cheap one (in budget) and an expensive one (over budget).
    The over-budget hotel is surfaced (not hidden) and flagged."""
    df, dt = "2026-08-01", "2026-08-08"
    fl = [{"price_per_person": 100, "summary": "v", "pricing_id": "f1", "departure_iata": "MXP",
           "date_from": df, "date_to": dt}]
    ho = [{"price_per_person": 100, "name": "Cheap", "stars": 4, "rating": 8.0,
           "hotel_internal_id": 1, "date_from": df, "date_to": dt},
          {"price_per_person": 2000, "name": "Pricey", "stars": 5, "rating": 9.0,
           "hotel_internal_id": 2, "date_from": df, "date_to": dt}]
    state = {"budget_per_person": 500, "currency": "EUR", "adults": 1, "min_stars": None,
             "destinations": [{"iata": "TFS", "name": "Tenerife"}],
             "flights": {"TFS": fl}, "hotels": {"TFS": ho}, "packages": {}}
    out = await optimizer_node(state)
    ranked = out["ranked"]
    over = next(c for c in ranked if c["price_per_person"] == 2100)
    assert any("budget" in w.lower() for w in over["unmet"])


@pytest.mark.asyncio
async def test_optimizer_flight_only_mode_emits_flight_cards():
    """search_mode=flight_only: one card per itinerary, no hotels/packages consulted."""
    df, dt = "2026-08-01", "2026-08-08"
    fl = [{"price_per_person": 120, "summary": "MXP→ATH 10:00", "airline": "Aegean",
           "deeplink": "https://lm/f1", "departure_iata": "MXP", "date_from": df, "date_to": dt},
          {"price_per_person": 95, "summary": "MXP→ATH 06:00", "airline": "Ryanair",
           "deeplink": "https://lm/f2", "departure_iata": "MXP", "date_from": df, "date_to": dt}]
    ho = [{"price_per_person": 300, "name": "Hotel X", "stars": 4, "rating": 8.5,
           "hotel_internal_id": 1, "date_from": df, "date_to": dt}]
    state = {"search_mode": "flight_only", "budget_per_person": 200, "currency": "EUR",
             "adults": 1, "min_stars": 4,
             "destinations": [{"iata": "ATH", "name": "Atene"}],
             "flights": {"ATH": fl}, "hotels": {"ATH": ho}, "packages": {}}
    out = await optimizer_node(state)
    ranked = out["ranked"]
    assert ranked and all(c["kind"] == "flight_only" for c in ranked)
    assert ranked[0]["price_per_person"] == 95          # cheapest first
    assert all(c["hotel_name"] is None for c in ranked)
    # min_stars must NOT flag flight cards (there is no hotel on them).
    assert all(not any("★" in w for w in c["unmet"]) for c in ranked)
    # best_value is rating-based: no hotel ratings -> no arbitrary best_value badge.
    assert all(c["badge"] != "best_value" for c in ranked)


@pytest.mark.asyncio
async def test_optimizer_flight_hotel_falls_back_to_hotels_when_flights_missing():
    """Regression: with no flight results for a period (bad IATA / MCP error), the hotels of
    that period must surface as hotel-only cards instead of being silently dropped."""
    df, dt = "2026-08-01", "2026-08-08"
    ho = [{"price_per_person": 320, "name": "Hotel Y", "stars": 4, "rating": 8.8,
           "hotel_internal_id": 7, "date_from": df, "date_to": dt}]
    state = {"budget_per_person": 1000, "currency": "EUR", "adults": 2, "min_stars": None,
             "destinations": [{"iata": "JTR", "name": "Santorini"}],
             "flights": {"JTR": []}, "hotels": {"JTR": ho}, "packages": {}}
    out = await optimizer_node(state)
    ranked = out["ranked"]
    assert len(ranked) == 1
    assert ranked[0]["kind"] == "hotel_only"
    assert ranked[0]["hotel_name"] == "Hotel Y"


@pytest.mark.asyncio
async def test_optimizer_hotel_only_mode_without_no_flight_flag():
    """search_mode=hotel_only must work on its own (the user wants only a hotel, not
    necessarily an overland trip): flights are ignored even when present."""
    df, dt = "2026-08-01", "2026-08-08"
    fl = [{"price_per_person": 100, "summary": "v", "departure_iata": "MXP",
           "date_from": df, "date_to": dt}]
    ho = [{"price_per_person": 250, "name": "Hotel Z", "stars": 5, "rating": 9.1,
           "hotel_internal_id": 3, "date_from": df, "date_to": dt}]
    state = {"search_mode": "hotel_only", "budget_per_person": 1000, "currency": "EUR",
             "adults": 1, "min_stars": None,
             "destinations": [{"iata": "FCO", "name": "Roma"}],
             "flights": {"FCO": fl}, "hotels": {"FCO": ho}, "packages": {}}
    out = await optimizer_node(state)
    ranked = out["ranked"]
    assert len(ranked) == 1
    assert ranked[0]["kind"] == "hotel_only"
    assert ranked[0]["price_per_person"] == 250          # flight NOT added
