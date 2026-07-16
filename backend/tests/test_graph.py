# backend/tests/test_graph.py
import json
import pytest
from langgraph.graph import END
from app.agent.graph import build_graph, after_scout


def test_after_scout_routes_by_search_mode():
    dests = [{"name": "Atene", "iata": "ATH"}]
    assert after_scout({"no_flight": True, "destinations": dests}) == ["hotel"]
    assert after_scout({"search_mode": "hotel_only", "destinations": dests}) == ["hotel"]
    assert after_scout({"search_mode": "flight_only", "destinations": dests}) == ["flight"]
    assert set(after_scout({"destinations": dests})) == {"flight", "hotel", "package"}
    assert set(after_scout({"search_mode": "flight_hotel", "destinations": dests})) == {
        "flight", "hotel", "package"}
    assert after_scout({"pending_question": {"x": 1}}) is END
    # No destinations and no question (conversational reply / empty proposal) -> end the turn.
    assert after_scout({}) is END
    assert after_scout({"destinations": [], "final_message": "ciao"}) is END

class StubLLM:
    async def complete_json(self, system, user):
        if "Intake" in system:
            return {"date_from": "2026-08-19", "date_to": "2026-08-26", "nights": 7, "adults": 2,
                    "budget_per_person": 750, "min_stars": 4, "destination_hint": "Canarie"}
        return {"destinations": [{"name": "Tenerife", "iata": "TFS", "reason": "Canarie"}]}
    async def complete_text(self, system, user): return "Proposte pronte."
    async def complete(self, messages, tools): return type("M", (), {"content": "[]", "tool_calls": None})()

class StubMcp:
    async def list_openai_tools(self): return []
    async def call_tool(self, name, args):
        if name.endswith("search_flight_and_hotel_package"):
            return json.dumps({"products_summary": [
                {"internal_id_hotel": 1, "name": "H", "stars": 4, "rating": 80, "price_total": 1400.0}]})
        return "[]"

@pytest.mark.asyncio
async def test_graph_stops_at_scout_to_confirm_destination():
    """With all required fields present, the graph proposes destinations and waits (always confirm)."""
    g = build_graph(StubLLM(), StubMcp())
    state = {"chat_id": 1, "origin_coords": (45.46, 9.19),
             "messages": [{"role": "user", "content": "Canarie agosto 2 persone 750€ 4 stelle"}]}
    final = await g.ainvoke(state, config={"configurable": {"thread_id": "t1"}})
    q = final.get("pending_question")
    assert q is not None and q["id"] == "selected_destination"
    assert final.get("final_message") in (None, "")
    assert [o["value"] for o in q["options"]] == ["TFS"]

@pytest.mark.asyncio
async def test_graph_runs_to_presenter_after_destination_selected():
    g = build_graph(StubLLM(), StubMcp())
    state = {"chat_id": 1, "origin_coords": (45.46, 9.19),
             "selected_destination": "TFS",
             "scout_candidates": [{"name": "Tenerife", "iata": "TFS", "reason": "Canarie"}],
             "messages": [{"role": "user", "content": "Canarie agosto 2 persone 750€ 4 stelle"}]}
    final = await g.ainvoke(state, config={"configurable": {"thread_id": "t1b"}})
    assert final.get("final_message") == "Proposte pronte."
    assert "ranked" in final

@pytest.mark.asyncio
async def test_graph_stops_at_question_when_budget_missing():
    class NoBudget(StubLLM):
        async def complete_json(self, system, user):
            if "Intake" in system:
                return {"date_from": "2026-08-19", "nights": 7, "adults": 2, "budget_per_person": None,
                        "min_stars": 4, "destination_hint": "Canarie"}
            return {"destinations": []}
    g = build_graph(NoBudget(), StubMcp())
    state = {"chat_id": 1, "origin_coords": (45.46, 9.19),
             "messages": [{"role": "user", "content": "Canarie agosto"}]}
    final = await g.ainvoke(state, config={"configurable": {"thread_id": "t2"}})
    assert final.get("pending_question") is not None
    assert final.get("final_message") in (None, "")


@pytest.mark.asyncio
async def test_intake_does_not_reask_duration_across_turns():
    """Regression (Test 08): once duration is known, a later turn whose intake re-extraction
    loses it (nights=null) must NOT re-ask — the checkpointed trip_nights is preserved.

    Verifies both the LangGraph checkpoint carries the slot into the next intake run AND the
    merge fix keeps it. Without the fix the second turn stops at a `trip_nights` question."""
    from langgraph.checkpoint.memory import MemorySaver

    class ForgetfulLLM(StubLLM):
        """Full brief on the first intake call, then null re-extraction (the ambiguous
        concatenated-text case) on every later intake call."""
        def __init__(self):
            self.intake_calls = 0
        async def complete_json(self, system, user):
            if "Intake" in system:
                self.intake_calls += 1
                if self.intake_calls == 1:
                    return {"date_from": "2026-08-19", "date_to": "2026-08-26", "nights": 7,
                            "adults": 2, "budget_per_person": 750, "min_stars": 4,
                            "destination_hint": "Canarie"}
                return {"date_from": None, "date_to": None, "nights": None, "adults": None,
                        "budget_per_person": None, "min_stars": None, "destination_hint": None}
            return {"destinations": [{"name": "Tenerife", "iata": "TFS", "reason": "Canarie"}]}

    g = build_graph(ForgetfulLLM(), StubMcp(), checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "t08"}}

    # Turn 1: full brief → proceeds to scout, which stops to confirm the destination.
    first = await g.ainvoke(
        {"chat_id": 1, "origin_coords": (45.46, 9.19),
         "messages": [{"role": "user", "content": "Canarie agosto 2 persone 750€ 4 stelle 7 notti"}]}, cfg)
    assert first.get("pending_question", {}).get("id") == "selected_destination"

    # Turn 2: the user picks a destination; intake re-runs first and now extracts all-null.
    # The duration must survive from the checkpoint, so we do NOT see a trip_nights question.
    second = await g.ainvoke(
        {"selected_destination": "TFS",
         "scout_candidates": [{"name": "Tenerife", "iata": "TFS", "reason": "Canarie"}],
         "messages": [{"role": "user", "content": "TFS"}]}, cfg)
    q = second.get("pending_question")
    assert q is None or q.get("id") != "trip_nights"
    assert second.get("trip_nights") == 7
    assert second.get("final_message") == "Proposte pronte."
