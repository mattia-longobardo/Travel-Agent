import pytest
from app.agent.stream import run_graph_events


class FakeGraph:
    """Simula astream emettendo aggiornamenti per nodo."""
    def __init__(self, updates, final):
        self._updates = updates
        self._final = final

    async def astream(self, state, config, stream_mode="updates"):
        for u in self._updates:
            yield u

    async def aget_state(self, config):
        return type("S", (), {"values": self._final})()


@pytest.mark.asyncio
async def test_events_include_steps_packages_and_done():
    updates = [
        {"intake": {"pending_question": None}},
        {"scout": {"destinations": [{"iata": "TFS"}]}},
        {"optimizer": {"ranked": []}},
        {"presenter": {"final_message": "ok"}},
    ]
    final = {
        "pending_question": None,
        "final_message": "ok",
        "ranked": [{"id": "pkg-1", "destination": "Tenerife (TFS)", "price_per_person": 350}],
    }
    evs = [e async for e in run_graph_events(FakeGraph(updates, final), {}, "t1")]
    types = [e["type"] for e in evs]
    assert "agent_step" in types
    assert types.count("package") == 1
    assert types[-1] == "done"
    assert any(e["type"] == "message" and e["content"] == "ok" for e in evs)


@pytest.mark.asyncio
async def test_emits_brief_before_question():
    q = {"type": "question", "id": "adults", "text": "?", "options": [], "allow_free_text": True}
    final = {
        "pending_question": q, "final_message": "",
        "date_from": "2026-08-16", "date_to": None, "adults": 2,
        "children_ages": [], "budget_per_person": 800.0, "currency": "EUR",
        "min_stars": 4, "origin_iata": ["MXP"],
        "constraints": {"destination_hint": "mare"},
    }
    evs = [e async for e in run_graph_events(
        FakeGraph([{"intake": {"pending_question": q}}], final), {}, "t1")]
    briefs = [e for e in evs if e["type"] == "brief"]
    assert len(briefs) == 1
    data = briefs[0]["data"]
    assert data["destination_hint"] == "mare"
    assert data["budget_per_person"] == 800.0
    assert data["origin_iata"] == ["MXP"]
    idx = [e["type"] for e in evs]
    assert idx.index("brief") < idx.index("question")


@pytest.mark.asyncio
async def test_brief_includes_window_and_flexible_flag():
    final = {
        "pending_question": None, "final_message": "ok", "ranked": [],
        "dates_flexible": True,
        "window_from": "2026-08-18", "window_to": "2026-08-31", "trip_nights": 7,
        "date_from": "2026-08-18", "date_to": "2026-08-25",
        "constraints": {"destination_hint": "mare"},
    }
    evs = [e async for e in run_graph_events(
        FakeGraph([{"intake": {"pending_question": None}}], final), {}, "t1")]
    briefs = [e for e in evs if e["type"] == "brief"]
    assert len(briefs) == 1
    data = briefs[0]["data"]
    assert data["window_from"] == "2026-08-18"
    assert data["window_to"] == "2026-08-31"
    assert data["trip_nights"] == 7
    assert data["dates_flexible"] is True


@pytest.mark.asyncio
async def test_brief_includes_min_stars_and_no_board_pool():
    """min_stars (the only filterable hotel preference) is emitted; board/pool are gone."""
    final = {
        "pending_question": None, "final_message": "ok", "ranked": [],
        "min_stars": 4,
        "constraints": {"destination_hint": "mare"},
    }
    evs = [e async for e in run_graph_events(
        FakeGraph([{"intake": {"pending_question": None}}], final), {}, "t1")]
    data = [e for e in evs if e["type"] == "brief"][0]["data"]
    assert data["min_stars"] == 4
    assert "board" not in data


@pytest.mark.asyncio
async def test_brief_includes_preferred_hotels():
    """Bug A Task 4: the brief snapshot carries preferred_hotels (additive)."""
    final = {
        "pending_question": None, "final_message": "ok", "ranked": [],
        "preferred_hotels": ["Anantara Qasr Al Sareb"],
        "constraints": {"destination_hint": None},
    }
    evs = [e async for e in run_graph_events(
        FakeGraph([{"intake": {"pending_question": None}}], final), {}, "t1")]
    data = [e for e in evs if e["type"] == "brief"][0]["data"]
    assert data["preferred_hotels"] == ["Anantara Qasr Al Sareb"]
    assert "pool" not in data


@pytest.mark.asyncio
async def test_brief_includes_search_and_accommodation_modes():
    final = {
        "pending_question": None, "final_message": "ok", "ranked": [],
        "search_mode": "hotel_only", "accommodation_type": "home",
        "accommodation_area": "Trastevere",
        "constraints": {"destination_hint": "Roma"},
    }
    evs = [e async for e in run_graph_events(
        FakeGraph([{"intake": {"pending_question": None}}], final), {}, "t1")]
    data = [e for e in evs if e["type"] == "brief"][0]["data"]
    assert data["search_mode"] == "hotel_only"
    assert data["accommodation_type"] == "home"
    assert data["accommodation_area"] == "Trastevere"


@pytest.mark.asyncio
async def test_events_emit_question_and_stop():
    q = {
        "type": "question",
        "id": "budget_per_person",
        "text": "?",
        "options": [],
        "allow_free_text": True,
    }
    final = {"pending_question": q, "final_message": ""}
    evs = [
        e
        async for e in run_graph_events(
            FakeGraph([{"intake": {"pending_question": q}}], final), {}, "t1"
        )
    ]
    assert any(e["type"] == "question" for e in evs)
    assert evs[-1]["type"] == "done"
    assert not any(e["type"] == "package" for e in evs)
