import pytest
from datetime import date
from app.agent.nodes.intake import intake_node

class StubLLM:
    def __init__(self, payload): self.payload = payload
    async def complete_json(self, system, user): return self.payload

class CapturingLLM:
    def __init__(self, payload): self.payload = payload; self.system = None
    async def complete_json(self, system, user):
        self.system = system; return self.payload


@pytest.mark.asyncio
async def test_intake_prompt_gives_today_and_resolves_relative_dates():
    """The system prompt must include today's date and instruct resolving relative
    Italian date expressions (e.g. 'ultime 2 settimane di agosto') to absolute dates."""
    state = {"messages": [{"role": "user", "content": "mare nelle ultime 2 settimane di agosto, 2 persone, 800€"}]}
    llm = CapturingLLM({"date_from": "2026-08-18", "date_to": "2026-08-31", "adults": 2,
                        "nights": 7, "budget_per_person": 800, "min_stars": 4,
                        "destination_hint": "mare"})
    out = await intake_node(state, llm)
    assert date.today().isoformat() in llm.system, "prompt must include today's date"
    assert "assolut" in llm.system.lower(), "prompt must instruct resolving to absolute dates"
    assert out.get("pending_question") is None
    assert out["date_from"] == "2026-08-18"

@pytest.mark.asyncio
async def test_intake_resolves_origin_from_coords_without_question():
    state = {"origin_coords": (45.46, 9.19),
             "messages": [{"role": "user", "content": "Canarie 2a metà agosto, 2 persone, max 750€"}]}
    llm = StubLLM({"date_from": "2026-08-19", "date_to": "2026-08-26", "dates_flexible": True,
                   "adults": 2, "nights": 7, "budget_per_person": 750, "min_stars": 4,
                   "destination_hint": "tipo Canarie"})
    out = await intake_node(state, llm)
    assert out["origin_iata"][0] in {"MXP", "LIN", "BGY"}
    assert out.get("pending_question") is None
    assert out["adults"] == 2 and out["budget_per_person"] == 750

@pytest.mark.asyncio
async def test_intake_prefill_answer_to_wins_over_llm():
    """Fix 1: prefill from answer_to must override LLM-extracted value (even null)."""
    state = {
        "origin_coords": (45.46, 9.19),
        "prefill": {"budget_per_person": 750},
        "messages": [{"role": "user", "content": "Canarie ad agosto"}],
    }
    # LLM returns null for budget — the prefill must win
    llm = StubLLM({"date_from": "2026-08-16", "date_to": "2026-08-23", "adults": 2,
                   "nights": 7, "budget_per_person": None, "min_stars": 4,
                   "destination_hint": "Canarie"})
    out = await intake_node(state, llm)
    assert out["budget_per_person"] == 750, "prefill must win over LLM null"
    assert out.get("pending_question") is None, "no question when prefill fills the gap"


@pytest.mark.asyncio
async def test_intake_asks_precompiled_question_when_budget_missing():
    state = {"origin_coords": (45.46, 9.19),
             "messages": [{"role": "user", "content": "Voglio andare alle Canarie ad agosto"}]}
    llm = StubLLM({"date_from": "2026-08-19", "date_to": "2026-08-26", "adults": 2,
                   "nights": 7, "budget_per_person": None, "min_stars": 4,
                   "destination_hint": "Canarie"})
    out = await intake_node(state, llm)
    q = out["pending_question"]
    assert q["id"] == "budget_per_person"
    assert q["allow_free_text"] is True
    assert len(q["options"]) >= 2


# Bug 1 — trip duration question ------------------------------------------------

@pytest.mark.asyncio
async def test_intake_asks_trip_nights_first_when_missing():
    """No duration volunteered → trip_nights is the first question, and trip_nights
    stays null in the output so the gap is detectable."""
    state = {"messages": [{"role": "user", "content": "vorrei andare al mare ad agosto con 1000€"}]}
    llm = StubLLM({"date_from": "2026-08-16", "date_to": None, "adults": 1,
                   "nights": None, "budget_per_person": 1000, "min_stars": None,
                   "destination_hint": "mare"})
    out = await intake_node(state, llm)
    assert out["trip_nights"] is None, "missing duration must stay null"
    assert out["missing"][0] == "trip_nights"
    assert out["pending_question"]["id"] == "trip_nights"
    assert out["pending_question"]["allow_free_text"] is True


@pytest.mark.asyncio
async def test_intake_prefill_trip_nights_satisfies_duration():
    """prefill trip_nights + date + budget present → no trip_nights question."""
    state = {
        "prefill": {"trip_nights": 10},
        "messages": [{"role": "user", "content": "mare ad agosto, 1000€"}],
    }
    llm = StubLLM({"date_from": "2026-08-16", "date_to": None, "adults": 1,
                   "nights": None, "budget_per_person": 1000, "min_stars": None,
                   "destination_hint": "mare"})
    out = await intake_node(state, llm)
    assert out["trip_nights"] == 10
    q = out.get("pending_question")
    assert q is None or q["id"] != "trip_nights"


@pytest.mark.asyncio
async def test_intake_explicit_nights_not_asked():
    """Explicit duration extracted by the LLM ('10 giorni') → trip_nights not asked."""
    state = {"messages": [{"role": "user", "content": "10 giorni al mare ad agosto, 1000€"}]}
    llm = StubLLM({"date_from": "2026-08-16", "date_to": None, "adults": 1,
                   "nights": 10, "budget_per_person": 1000, "min_stars": None,
                   "destination_hint": "mare"})
    out = await intake_node(state, llm)
    assert out["trip_nights"] == 10
    q = out.get("pending_question")
    assert q is None or q["id"] != "trip_nights"


# Bug 4 — hotel-category (stars) question; board/pool removed (not filterable) -----

@pytest.mark.asyncio
async def test_intake_asks_stars_when_no_pref():
    """Required satisfied, no min_stars → ask the hotel-category question once."""
    state = {"messages": [{"role": "user", "content": "una settimana al mare ad agosto, 1000€"}]}
    llm = StubLLM({"date_from": "2026-08-16", "date_to": None, "adults": 1,
                   "nights": 7, "budget_per_person": 1000, "min_stars": None,
                   "destination_hint": "mare"})
    out = await intake_node(state, llm)
    assert out["pending_question"]["id"] == "min_stars"
    assert out["preferences_asked"] is True


@pytest.mark.asyncio
async def test_intake_stars_not_asked_when_volunteered():
    """User volunteered min_stars → the hotel-category question is not asked."""
    state = {"messages": [{"role": "user", "content": "una settimana al mare ad agosto, 1000€, hotel 4 stelle"}]}
    llm = StubLLM({"date_from": "2026-08-16", "date_to": None, "adults": 1,
                   "nights": 7, "budget_per_person": 1000, "min_stars": 4,
                   "destination_hint": "mare"})
    out = await intake_node(state, llm)
    assert out.get("pending_question") is None


@pytest.mark.asyncio
async def test_intake_stars_prefill_sets_min_stars():
    """Answering the hotel-category question sets min_stars directly via prefill."""
    state = {
        "preferences_asked": True,
        "prefill": {"min_stars": 4},
        "messages": [{"role": "user", "content": "una settimana al mare ad agosto, 1000€"}],
    }
    llm = StubLLM({"date_from": "2026-08-16", "date_to": None, "adults": 1,
                   "nights": 7, "budget_per_person": 1000, "min_stars": None,
                   "destination_hint": "mare"})
    out = await intake_node(state, llm)
    assert out["min_stars"] == 4
    assert out.get("pending_question") is None


@pytest.mark.asyncio
async def test_intake_stars_indifferent_proceeds():
    """'Indifferente' (0) leaves no star filter and does not re-ask."""
    state = {
        "preferences_asked": True,
        "prefill": {"min_stars": 0},
        "messages": [{"role": "user", "content": "una settimana al mare ad agosto, 1000€"}],
    }
    llm = StubLLM({"date_from": "2026-08-16", "date_to": None, "adults": 1,
                   "nights": 7, "budget_per_person": 1000, "min_stars": None,
                   "destination_hint": "mare"})
    out = await intake_node(state, llm)
    assert not out.get("min_stars")
    assert out.get("pending_question") is None


@pytest.mark.asyncio
async def test_intake_required_takes_priority_over_stars():
    """Budget missing → ask budget, not the hotel-category question."""
    state = {"messages": [{"role": "user", "content": "una settimana al mare ad agosto"}]}
    llm = StubLLM({"date_from": "2026-08-16", "date_to": None, "adults": 1,
                   "nights": 7, "budget_per_person": None, "min_stars": None,
                   "destination_hint": "mare"})
    out = await intake_node(state, llm)
    assert out["pending_question"]["id"] == "budget_per_person"


# Test 08 — a slot answered once must not be re-asked on a later turn -------------

@pytest.mark.asyncio
async def test_intake_preserves_prior_slots_when_reextraction_is_null():
    """Regression (Test 08): after the user answered duration/period/budget (now in the
    checkpointed state), a later turn whose LLM extraction returns nulls must NOT wipe them
    and re-ask. The graph re-enters intake every turn, so this is the double-ask root cause."""
    state = {
        "trip_nights": 7, "date_from": "2026-08-16", "budget_per_person": 1000,
        "min_stars": 4, "preferences_asked": True,
        "constraints": {"destination_hint": "mare"},
        "messages": [{"role": "user", "content": "Voglio andare al mare"},
                     {"role": "user", "content": "7"},
                     {"role": "user", "content": "2026-08-16"}],
    }
    llm = StubLLM({"date_from": None, "date_to": None, "adults": None,
                   "nights": None, "budget_per_person": None, "min_stars": None,
                   "destination_hint": None})
    out = await intake_node(state, llm)
    assert out["trip_nights"] == 7
    assert out["date_from"] == "2026-08-16"
    assert out["budget_per_person"] == 1000
    assert out["min_stars"] == 4
    q = out.get("pending_question")
    assert q is None or q["id"] != "trip_nights"


# Bug B Task 4 — a vague budget is stored as None (defense in depth) --------------

@pytest.mark.asyncio
async def test_intake_vague_budget_stored_as_none():
    state = {"messages": [{"role": "user", "content": "mare ad agosto, 7 notti"}]}
    llm = StubLLM({"date_from": "2026-08-16", "date_to": None, "adults": 1,
                   "nights": 7, "budget_per_person": "quel che serve", "min_stars": None,
                   "destination_hint": "mare"})
    out = await intake_node(state, llm)
    assert out["budget_per_person"] is None


# Bug A Task 1 — preferred_hotels extraction (sticky) -----------------------------

@pytest.mark.asyncio
async def test_intake_captures_preferred_hotels():
    state = {"messages": [{"role": "user", "content": "vorrei stare all'Anantara Qasr Al Sareb"}]}
    llm = StubLLM({"date_from": "2026-12-04", "date_to": "2026-12-14", "adults": 1,
                   "nights": 10, "budget_per_person": 2000, "min_stars": None,
                   "preferred_hotels": ["Anantara Qasr Al Sareb", "Anantara Al Jabal Al Akhdar"],
                   "destination_hint": None})
    out = await intake_node(state, llm)
    assert out["preferred_hotels"] == ["Anantara Qasr Al Sareb", "Anantara Al Jabal Al Akhdar"]


@pytest.mark.asyncio
async def test_intake_preferred_hotels_sticky_across_null_reextraction():
    state = {"preferred_hotels": ["Anantara Qasr Al Sareb"],
             "trip_nights": 10, "date_from": "2026-12-04", "budget_per_person": 2000,
             "preferences_asked": True,
             "messages": [{"role": "user", "content": "Anantara"}]}
    llm = StubLLM({"date_from": None, "date_to": None, "adults": None, "nights": None,
                   "budget_per_person": None, "min_stars": None,
                   "preferred_hotels": None, "destination_hint": None})
    out = await intake_node(state, llm)
    assert out["preferred_hotels"] == ["Anantara Qasr Al Sareb"]


# Imp2 Task 1 — no_flight extraction (sticky) -------------------------------------

@pytest.mark.asyncio
async def test_intake_captures_no_flight():
    state = {"messages": [{"role": "user", "content": "viaggio in auto, on the road, 1000€, 7 notti, ad agosto"}]}
    llm = StubLLM({"date_from": "2026-08-16", "date_to": None, "adults": 1,
                   "nights": 7, "budget_per_person": 1000, "min_stars": None,
                   "no_flight": True, "destination_hint": "on the road"})
    out = await intake_node(state, llm)
    assert out["no_flight"] is True


@pytest.mark.asyncio
async def test_intake_no_flight_sticky_across_null_reextraction():
    state = {"no_flight": True, "trip_nights": 7, "date_from": "2026-08-16",
             "budget_per_person": 1000, "preferences_asked": True,
             "messages": [{"role": "user", "content": "in auto"}]}
    llm = StubLLM({"date_from": None, "date_to": None, "adults": None, "nights": None,
                   "budget_per_person": None, "min_stars": None,
                   "no_flight": None, "destination_hint": None})
    out = await intake_node(state, llm)
    assert out["no_flight"] is True


@pytest.mark.asyncio
async def test_intake_no_flight_defaults_false():
    state = {"messages": [{"role": "user", "content": "mare ad agosto, 7 notti, 1000€"}]}
    llm = StubLLM({"date_from": "2026-08-16", "date_to": None, "adults": 1,
                   "nights": 7, "budget_per_person": 1000, "min_stars": None,
                   "destination_hint": "mare"})
    out = await intake_node(state, llm)
    assert out["no_flight"] is False


# Imp1 Task 2 — origin uses nearest-airport fallback beyond 80 km -----------------

@pytest.mark.asyncio
async def test_intake_origin_uses_nearest_fallback_beyond_radius():
    state = {"origin_coords": (40.0, -30.0),  # mid-Atlantic, nothing within 80 km
             "messages": [{"role": "user", "content": "mare ad agosto, 7 notti, 1000€"}]}
    llm = StubLLM({"date_from": "2026-08-16", "date_to": None, "adults": 1,
                   "nights": 7, "budget_per_person": 1000, "min_stars": None,
                   "destination_hint": "mare"})
    out = await intake_node(state, llm)
    assert isinstance(out["origin_iata"], list) and len(out["origin_iata"]) >= 1


@pytest.mark.asyncio
async def test_intake_restated_value_still_overrides_prior():
    """A user who restates a value (non-null extraction) still overrides the prior one."""
    state = {
        "trip_nights": 7, "date_from": "2026-08-16", "budget_per_person": 1000,
        "min_stars": 4, "preferences_asked": True,
        "constraints": {"destination_hint": "mare"},
        "messages": [{"role": "user", "content": "Voglio andare al mare, anzi facciamo 10 giorni"}],
    }
    llm = StubLLM({"date_from": None, "date_to": None, "adults": None,
                   "nights": 10, "budget_per_person": None, "min_stars": None,
                   "destination_hint": None})
    out = await intake_node(state, llm)
    assert out["trip_nights"] == 10


@pytest.mark.asyncio
async def test_intake_resets_generate_more_and_refine_text_every_turn():
    """Loop fix: generate_more/refine_text are per-turn UI flags. Once checkpointed True they
    used to stay True forever (nothing reset them), so the scout re-proposed destinations on
    every later turn. Intake must reset them unless this turn's prefill re-sets them."""
    base = {"date_from": "2026-08-16", "date_to": "2026-08-23", "adults": 2, "nights": 7,
            "budget_per_person": 800, "min_stars": 4, "destination_hint": "Canarie"}
    # Sticky True from a previous turn, no prefill this turn -> reset.
    state = {"generate_more": True, "refine_text": "più verso la Grecia",
             "messages": [{"role": "user", "content": "ok la prima"}]}
    out = await intake_node(state, StubLLM(base))
    assert out["generate_more"] is False
    assert out["refine_text"] is None
    # Prefill set this turn -> kept for this turn only.
    state = {"generate_more": False,
             "prefill": {"generate_more": True, "refine_text": "tipo Grecia"},
             "messages": [{"role": "user", "content": "genera altre opzioni"}]}
    out = await intake_node(state, StubLLM(base))
    assert out["generate_more"] is True
    assert out["refine_text"] == "tipo Grecia"


@pytest.mark.asyncio
async def test_intake_extracts_search_mode_and_keeps_it_sticky():
    base = {"date_from": "2026-08-16", "date_to": "2026-08-23", "adults": 2, "nights": 7,
            "budget_per_person": 800, "min_stars": 3, "destination_hint": "Roma"}
    # Extracted hotel_only wins.
    out = await intake_node({"messages": [{"role": "user", "content": "solo hotel a Roma"}]},
                            StubLLM({**base, "search_mode": "hotel_only"}))
    assert out["search_mode"] == "hotel_only"
    # Null re-extraction must not wipe the prior mode.
    out = await intake_node({"search_mode": "flight_only",
                             "messages": [{"role": "user", "content": "ok"}]},
                            StubLLM({**base, "search_mode": None}))
    assert out["search_mode"] == "flight_only"
    # Invalid value falls back to the default comparison.
    out = await intake_node({"messages": [{"role": "user", "content": "vacanza"}]},
                            StubLLM({**base, "search_mode": "banana"}))
    assert out["search_mode"] == "flight_hotel"
    # Overland trips are hotel-only regardless of the extracted mode.
    out = await intake_node({"messages": [{"role": "user", "content": "on the road"}]},
                            StubLLM({**base, "no_flight": True, "search_mode": "flight_hotel"}))
    assert out["search_mode"] == "hotel_only"


@pytest.mark.asyncio
async def test_intake_prefill_preserves_explicit_mode_and_accommodation_type():
    base = {"date_from": "2026-08-16", "date_to": "2026-08-23", "adults": 2, "nights": 7,
            "budget_per_person": 800, "min_stars": 3, "destination_hint": "Roma",
            "search_mode": "flight_hotel", "accommodation_type": "hotel"}
    state = {
        "prefill": {"search_mode": "hotel_only", "accommodation_type": "home"},
        "messages": [{"role": "user", "content": "Roma"}],
    }
    out = await intake_node(state, StubLLM(base))
    assert out["search_mode"] == "hotel_only"
    assert out["accommodation_type"] == "home"

    # A later null extraction keeps both values from checkpointed state.
    out = await intake_node(
        {"search_mode": "hotel_only", "accommodation_type": "home",
         "messages": [{"role": "user", "content": "ok"}]},
        StubLLM({**base, "search_mode": None, "accommodation_type": None}),
    )
    assert out["search_mode"] == "hotel_only"
    assert out["accommodation_type"] == "home"


@pytest.mark.asyncio
async def test_intake_extracts_and_keeps_specific_accommodation_area():
    base = {"date_from": "2026-08-16", "date_to": "2026-08-23", "adults": 2,
            "nights": 7, "budget_per_person": 800, "min_stars": 3,
            "destination_hint": "Roma", "search_mode": "flight_hotel",
            "accommodation_type": "both"}
    out = await intake_node(
        {"messages": [{"role": "user", "content": "Roma, ma alloggio a Trastevere"}]},
        StubLLM({**base, "accommodation_area": "Trastevere"}),
    )
    assert out["accommodation_area"] == "Trastevere"

    # A later answer whose extraction omits the area must not erase the checkpointed choice.
    out = await intake_node(
        {"accommodation_area": "Trastevere",
         "messages": [{"role": "user", "content": "va bene 800 euro"}]},
        StubLLM({**base, "accommodation_area": None}),
    )
    assert out["accommodation_area"] == "Trastevere"

    # Empty string is the explicit clear signal described by the intake contract.
    out = await intake_node(
        {"accommodation_area": "Trastevere",
         "messages": [{"role": "user", "content": "qualsiasi zona va bene"}]},
        StubLLM({**base, "accommodation_area": ""}),
    )
    assert out["accommodation_area"] is None

@pytest.mark.asyncio
async def test_intake_budget_question_scope_follows_mode():
    """The budget question must say what it covers: volo+hotel, solo hotel or solo volo."""
    base = {"date_from": "2026-08-16", "date_to": "2026-08-23", "adults": 2, "nights": 7,
            "budget_per_person": None, "min_stars": None, "destination_hint": "Roma"}
    out = await intake_node({"messages": [{"role": "user", "content": "solo hotel a Roma"}]},
                            StubLLM({**base, "search_mode": "hotel_only"}))
    assert out["pending_question"]["id"] == "budget_per_person"
    assert "solo alloggio" in out["pending_question"]["text"]
    out = await intake_node({"messages": [{"role": "user", "content": "solo volo per Roma"}]},
                            StubLLM({**base, "search_mode": "flight_only"}))
    assert "solo volo" in out["pending_question"]["text"]
    out = await intake_node({"messages": [{"role": "user", "content": "vacanza a Roma"}]},
                            StubLLM(base))
    assert "volo+hotel" in out["pending_question"]["text"]


@pytest.mark.asyncio
async def test_intake_skips_stars_question_for_flight_only():
    """No hotel is searched in flight-only mode: the star-category question is pointless."""
    base = {"date_from": "2026-08-16", "date_to": "2026-08-23", "adults": 2, "nights": 7,
            "budget_per_person": 800, "min_stars": None, "destination_hint": "Roma",
            "search_mode": "flight_only"}
    out = await intake_node({"messages": [{"role": "user", "content": "solo volo per Roma"}]},
                            StubLLM(base))
    assert out["pending_question"] is None


@pytest.mark.asyncio
async def test_intake_skips_stars_question_for_home_only():
    base = {"date_from": "2026-08-16", "date_to": "2026-08-23", "adults": 2, "nights": 7,
            "budget_per_person": 800, "min_stars": None, "destination_hint": "Roma",
            "search_mode": "hotel_only", "accommodation_type": "home"}
    out = await intake_node({"messages": [{"role": "user", "content": "una casa a Roma"}]},
                            StubLLM(base))
    assert out["pending_question"] is None


@pytest.mark.asyncio
async def test_explicit_ui_mode_clears_stale_no_flight():
    base = {"date_from": "2026-08-16", "date_to": "2026-08-23", "adults": 2, "nights": 7,
            "budget_per_person": 800, "min_stars": None, "destination_hint": "Roma",
            "search_mode": None, "accommodation_type": None, "no_flight": None}
    state = {"no_flight": True, "search_mode": "hotel_only",
             "prefill": {"search_mode": "flight_only", "accommodation_type": "both"},
             "messages": [{"role": "user", "content": "ora solo volo"}]}
    out = await intake_node(state, StubLLM(base))
    assert out["search_mode"] == "flight_only"
    assert out["no_flight"] is False
