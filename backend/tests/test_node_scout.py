import pytest
from app.agent.nodes.scout import scout_node, QUESTION_ID, RESOLVE_SYSTEM, SPECIFIC_SYSTEM

class StubLLM:
    def __init__(self, payload): self.payload = payload
    async def complete_json(self, system, user): return self.payload


class PromptAwareLLM:
    """Reproduces the real LLM's behaviour by branching on WHICH prompt it receives:
    - the 'propose alternatives' prompt (SYSTEM) returns NEARBY cities at similar distance
      (for 'New York' the model would naturally lead with Boston),
    - the 'resolve concrete' prompt (RESOLVE_SYSTEM) returns the NAMED city itself.
    A prompt-agnostic stub can't surface the New York→Boston bug; this can."""
    def __init__(self): self.calls = []
    async def complete_json(self, system, user):
        self.calls.append((system, user))
        if system is SPECIFIC_SYSTEM:
            return {"specific": True}
        if system is RESOLVE_SYSTEM:
            return {"destinations": [{"name": "New York", "iata": "JFK",
                                      "reason": "richiesta esplicita", "description": "La Grande Mela."}]}
        # alternatives prompt: nearby east-coast cities, Boston first (the old bug's output)
        return {"destinations": [
            {"name": "Boston", "iata": "BOS", "reason": "costa est, distanza simile", "description": "x"},
            {"name": "Filadelfia", "iata": "PHL", "reason": "vicino", "description": "y"}]}


@pytest.mark.asyncio
async def test_scout_specific_named_city_resolves_to_that_city_not_a_neighbor():
    """Regression (New York → Boston): a concrete destination must resolve to THAT city, never to
    a similar nearby one. The old code routed concrete hints through the 'propose alternatives'
    prompt, so 'New York' came back as Boston. It must yield JFK."""
    state = {"origin_iata": ["MXP"], "date_from": "2026-09-01",
             "constraints": {"destination_hint": "New York"}}
    llm = PromptAwareLLM()
    out = await scout_node(state, llm)
    assert out["pending_question"] is None
    assert [d["iata"] for d in out["destinations"]] == ["JFK"]


@pytest.mark.asyncio
async def test_scout_confirm_free_text_resolves_named_city_not_a_neighbor():
    """Same bug on the free-text 'confirm' path: typing 'New York' in the composer after proposals
    must resolve to New York itself, not to a nearby alternative."""
    candidates = [{"name": "Tenerife", "iata": "TFS", "reason": "x"}]
    state = {"origin_iata": ["MXP"], "scout_candidates": candidates,
             "selected_destination": "New York"}

    class ConfirmThenResolve(PromptAwareLLM):
        async def complete_json(self, system, user):
            # First call is the intent classifier (neither SPECIFIC nor RESOLVE) -> confirm.
            if system is not RESOLVE_SYSTEM and system is not SPECIFIC_SYSTEM and not self.calls:
                self.calls.append((system, user))
                return {"intent": "confirm"}
            return await super().complete_json(system, user)

    out = await scout_node(state, ConfirmThenResolve())
    assert out["pending_question"] is None
    assert [d["iata"] for d in out["destinations"]] == ["JFK"]

class SequenceLLM:
    """Returns queued payloads in order, one per complete_json call."""
    def __init__(self, *payloads): self.payloads = list(payloads); self.calls = []
    async def complete_json(self, system, user):
        self.calls.append((system, user))
        return self.payloads.pop(0) if self.payloads else {}

@pytest.mark.asyncio
async def test_scout_proposes_candidates_and_asks_before_searching():
    """Decision: always confirm — scout proposes options and STOPS for the user to pick."""
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19",
             "constraints": {"destination_hint": "tipo Azzorre o Canarie, non lontano"}}
    llm = StubLLM({"destinations": [
        {"name": "Tenerife", "iata": "TFS", "reason": "Canarie, clima mite, voli diretti da MXP",
         "description": "Isola vulcanica con spiagge nere; trekking sul Teide e mare."},
        {"name": "Gran Canaria", "iata": "LPA", "reason": "Canarie, spiagge",
         "description": "Dune di Maspalomas, surf e vita notturna."},
        {"name": "Funchal (Madeira)", "iata": "FNC", "reason": "Atlantico, simile alle Azzorre",
         "description": "Isola verde, levadas da percorrere a piedi."}]})
    out = await scout_node(state, llm)
    assert out["destinations"] == []                      # non cerca ancora
    assert len(out["scout_candidates"]) == 3
    q = out["pending_question"]
    assert q["id"] == QUESTION_ID and q["allow_free_text"] is True
    assert {o["value"] for o in q["options"]} == {"TFS", "LPA", "FNC"}

@pytest.mark.asyncio
async def test_scout_question_is_multi_select():
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19",
             "constraints": {"destination_hint": "mare"}}
    llm = StubLLM({"destinations": [
        {"name": "Creta", "iata": "HER", "reason": "isola greca", "description": "Spiagge."},
        {"name": "Tenerife", "iata": "TFS", "reason": "Canarie", "description": "Teide."}]})
    out = await scout_node(state, llm)
    assert out["pending_question"]["multi_select"] is True


@pytest.mark.asyncio
async def test_scout_resolves_comma_separated_to_multiple_destinations():
    """A comma-separated pick like 'HER,TFS' resolves to BOTH destinations and searches them."""
    candidates = [{"name": "Creta", "iata": "HER", "reason": "x"},
                  {"name": "Tenerife", "iata": "TFS", "reason": "y"},
                  {"name": "Gran Canaria", "iata": "LPA", "reason": "z"}]
    state = {"origin_iata": ["MXP"], "scout_candidates": candidates,
             "selected_destination": "HER,TFS"}
    llm = SequenceLLM()  # exact match short-circuits; no LLM call expected
    out = await scout_node(state, llm)
    assert out["pending_question"] is None
    assert [d["iata"] for d in out["destinations"]] == ["HER", "TFS"]
    assert llm.calls == []


@pytest.mark.asyncio
async def test_scout_options_carry_descriptions():
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19",
             "constraints": {"destination_hint": "al mare come la Spagna, altre proposte?"}}
    llm = StubLLM({"destinations": [
        {"name": "Tenerife", "iata": "TFS", "reason": "Canarie", "description": "Spiagge e Teide."},
        {"name": "Malta", "iata": "MLA", "reason": "Mediterraneo", "description": "Mare cristallino e storia."}]})
    out = await scout_node(state, llm)
    opts = out["pending_question"]["options"]
    assert all(o.get("description") for o in opts)
    by_val = {o["value"]: o["description"] for o in opts}
    assert by_val["TFS"] == "Spiagge e Teide."
    assert by_val["MLA"] == "Mare cristallino e storia."

@pytest.mark.asyncio
async def test_scout_caps_candidates_at_five():
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19", "constraints": {"destination_hint": "mare"}}
    many = [{"name": f"D{i}", "iata": f"X{i}", "reason": "r", "description": "d"} for i in range(8)]
    out = await scout_node(state, StubLLM({"destinations": many}))
    assert len(out["scout_candidates"]) == 5
    assert len(out["pending_question"]["options"]) == 5

@pytest.mark.asyncio
async def test_scout_searches_only_the_selected_destination():
    """Exact-match pick: resolves to that candidate, proceeds to search, no LLM intent call."""
    candidates = [{"name": "Tenerife", "iata": "TFS", "reason": "x"},
                  {"name": "Gran Canaria", "iata": "LPA", "reason": "y"}]
    state = {"origin_iata": ["MXP"], "scout_candidates": candidates, "selected_destination": "TFS"}
    llm = SequenceLLM()  # no payloads queued: a complete_json call would return {} but none should happen
    out = await scout_node(state, llm)
    assert out["pending_question"] is None
    assert [d["iata"] for d in out["destinations"]] == ["TFS"]
    assert llm.calls == []  # exact match short-circuits, no LLM

@pytest.mark.asyncio
async def test_scout_refine_reproposes_without_searching():
    candidates = [{"name": "Tenerife", "iata": "TFS", "reason": "x", "description": "Canarie"},
                  {"name": "Gran Canaria", "iata": "LPA", "reason": "y", "description": "Canarie"}]
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19",
             "scout_candidates": candidates,
             "constraints": {"destination_hint": "tipo Azzorre"},
             "selected_destination": "Pensavo a qualcosa piu come Grecia"}
    # 1st complete_json -> intent classifier (refine); 2nd -> fresh proposals reflecting Greece.
    llm = SequenceLLM(
        {"intent": "refine"},
        {"destinations": [
            {"name": "Atene", "iata": "ATH", "reason": "capitale greca", "description": "Acropoli e storia."},
            {"name": "Creta", "iata": "HER", "reason": "isola greca", "description": "Spiagge e Cnosso."},
            {"name": "Santorini", "iata": "JTR", "reason": "Cicladi", "description": "Tramonti e caldere."}]})
    out = await scout_node(state, llm)
    assert out["destinations"] == []                       # does NOT search
    q = out["pending_question"]
    assert q is not None and q["id"] == QUESTION_ID
    assert {o["value"] for o in q["options"]} == {"ATH", "HER", "JTR"}
    assert all(o.get("description") for o in q["options"])
    # new candidates persisted for the next turn's resolve
    assert {c["iata"] for c in out["scout_candidates"]} == {"ATH", "HER", "JTR"}

@pytest.mark.asyncio
async def test_scout_confirm_free_text_proceeds_to_search():
    candidates = [{"name": "Tenerife", "iata": "TFS", "reason": "x"},
                  {"name": "Gran Canaria", "iata": "LPA", "reason": "y"}]
    state = {"origin_iata": ["MXP"], "scout_candidates": candidates,
             "selected_destination": "Santorini"}
    # 1st complete_json -> intent classifier (confirm); 2nd -> map free text to airport(s).
    llm = SequenceLLM(
        {"intent": "confirm"},
        {"destinations": [{"name": "Santorini", "iata": "JTR", "reason": "Cicladi"}]})
    out = await scout_node(state, llm)
    assert out["pending_question"] is None
    assert out["destinations"] and out["destinations"][0]["iata"] == "JTR"

@pytest.mark.asyncio
async def test_scout_vague_destination_never_errors():
    """Bug B Task 5: a vague destination hint yields a question with options, never raises."""
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19",
             "constraints": {"destination_hint": "una qualunque città della Spagna"}}
    llm = StubLLM({"destinations": [
        {"name": "Barcellona", "iata": "BCN", "reason": "Spagna", "description": "Città d'arte."},
        {"name": "Madrid", "iata": "MAD", "reason": "Spagna", "description": "Capitale."},
        {"name": "Malaga", "iata": "AGP", "reason": "Spagna", "description": "Costa del Sol."}]})
    out = await scout_node(state, llm)
    q = out["pending_question"]
    assert q is not None and q["options"]


@pytest.mark.asyncio
async def test_scout_derives_destination_from_preferred_hotels():
    """Bug A Task 2: named hotels derive the destination directly, no question asked."""
    state = {"origin_iata": ["AUH"],
             "preferred_hotels": ["Anantara Qasr Al Sareb near Abu Dhabi",
                                  "Anantara Al Jabal Al Akhdar Oman"]}
    llm = StubLLM({"destinations": [{"name": "Abu Dhabi", "iata": "AUH"},
                                    {"name": "Muscat", "iata": "MCT"}]})
    out = await scout_node(state, llm)
    assert out["pending_question"] is None
    assert [d["iata"] for d in out["destinations"]] == ["AUH", "MCT"]


@pytest.mark.asyncio
async def test_scout_skips_question_for_specific_destination():
    """Task 4 / Item 1: a single concrete hint resolves directly, no proposal/question."""
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19",
             "constraints": {"destination_hint": "Tenerife"}}
    # 1st complete_json -> specificity classifier (specific=true);
    # 2nd -> _generate resolving the hint to the destination.
    llm = SequenceLLM(
        {"specific": True},
        {"destinations": [{"name": "Tenerife", "iata": "TFS", "reason": "Canarie",
                           "description": "Spiagge e Teide."}]})
    out = await scout_node(state, llm)
    assert out["pending_question"] is None
    assert [d["iata"] for d in out["destinations"]] == ["TFS"]


@pytest.mark.asyncio
async def test_scout_asks_when_hint_is_vague():
    """Task 4 / Item 1: a vague hint keeps the propose+ask behaviour."""
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19",
             "constraints": {"destination_hint": "al mare tipo Grecia"}}
    # 1st complete_json -> specificity classifier (specific=false);
    # 2nd -> _generate proposing candidates.
    llm = SequenceLLM(
        {"specific": False},
        {"destinations": [
            {"name": "Creta", "iata": "HER", "reason": "isola greca", "description": "Spiagge."},
            {"name": "Atene", "iata": "ATH", "reason": "capitale", "description": "Acropoli."}]})
    out = await scout_node(state, llm)
    assert out.get("pending_question") is not None
    assert out["scout_candidates"]
    assert {o["value"] for o in out["pending_question"]["options"]} == {"HER", "ATH"}


@pytest.mark.asyncio
async def test_scout_asks_when_classifier_errors():
    """Task 4 / Item 1: 'nel dubbio false' — a failing classifier must NOT skip the question."""
    class BoomThenGenerate:
        def __init__(self): self.n = 0
        async def complete_json(self, system, user):
            self.n += 1
            if self.n == 1:
                raise RuntimeError("classifier exploded")
            return {"destinations": [
                {"name": "Creta", "iata": "HER", "reason": "x", "description": "y"}]}
    out = await scout_node(
        {"origin_iata": ["MXP"], "date_from": "2026-08-19",
         "constraints": {"destination_hint": "mare"}}, BoomThenGenerate())
    assert out.get("pending_question") is not None


@pytest.mark.asyncio
async def test_scout_accumulates_pool_and_proceeds_when_le_5():
    """Task 5 / Item 3: newly picked candidates merge into the pool; with ≤5 -> proceed, no question."""
    candidates = [{"name": "A", "iata": "AAA"}, {"name": "B", "iata": "BBB"}]
    state = {"scout_candidates": candidates, "selected_destination": "AAA,BBB",
             "selected_pool": [], "generate_more": False}
    llm = SequenceLLM()  # exact picks resolve without an LLM call
    out = await scout_node(state, llm)
    assert {d["iata"] for d in out["destinations"]} == {"AAA", "BBB"}
    assert out.get("pending_question") is None
    # The episode closes when the search starts: picks/candidates reset for the next round.
    assert out["selected_pool"] == []
    assert out["scout_candidates"] == []
    assert out["selected_destination"] is None
    assert out["scout_rounds"] == 0
    assert llm.calls == []


@pytest.mark.asyncio
async def test_scout_generate_more_keeps_pool_and_reasks():
    """Task 5 / Item 3: generate_more keeps the pool and proposes a FRESH batch excluding pooled iatas."""
    state = {"scout_candidates": [{"name": "A", "iata": "AAA"}],
             "selected_destination": "AAA", "selected_pool": [],
             "generate_more": True}
    # _generate returns a batch that includes an already-pooled iata (AAA) -> must be excluded.
    llm = StubLLM({"destinations": [
        {"name": "A", "iata": "AAA", "reason": "old", "description": "x"},
        {"name": "C", "iata": "CCC", "reason": "new", "description": "y"}]})
    out = await scout_node(state, llm)
    assert out.get("pending_question") is not None
    assert any(d["iata"] == "AAA" for d in out["selected_pool"])      # pool kept
    assert all(d["iata"] != "AAA" for d in out["scout_candidates"])   # fresh batch excludes pooled
    assert {c["iata"] for c in out["scout_candidates"]} == {"CCC"}
    assert out["destinations"] == []


@pytest.mark.asyncio
async def test_scout_asks_to_trim_to_5_when_pool_gt_5():
    """Task 5 / Item 3: a pool above 5 yields a multi_select over the pool asking to pick exactly 5."""
    pool = [{"name": n, "iata": n} for n in ["A", "B", "C", "D", "E", "F"]]
    state = {"scout_candidates": [], "selected_destination": "", "selected_pool": pool,
             "generate_more": False}
    llm = SequenceLLM()  # no resolution needed; pool decides
    out = await scout_node(state, llm)
    q = out.get("pending_question")
    assert q and q.get("multi_select") and len(q["options"]) == 6
    assert "5" in q["text"]
    assert out["destinations"] == []
    assert {d["iata"] for d in out["selected_pool"]} == set("ABCDEF")
    assert llm.calls == []


@pytest.mark.asyncio
async def test_scout_maps_free_text_choice_defaults_to_refine_when_ambiguous():
    """Free text not among candidates, ambiguous classifier -> defaults to refine and re-proposes."""
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19",
             "scout_candidates": [], "selected_destination": "qualcosa in Grecia"}
    # ambiguous intent (empty) -> default refine -> re-propose
    llm = SequenceLLM(
        {},
        {"destinations": [{"name": "Rodi", "iata": "RHO", "reason": "isola greca", "description": "Mare e centro storico."}]})
    out = await scout_node(state, llm)
    assert out["destinations"] == []
    assert out["pending_question"]["options"][0]["value"] == "RHO"


@pytest.mark.asyncio
async def test_scout_proceed_free_text_searches_current_candidates():
    """Loop fix: the user signals 'these proposals are fine, go ahead' (no new pick). Exit the
    propose-loop and search the destinations already on the table instead of re-proposing."""
    candidates = [{"name": "Creta", "iata": "HER", "reason": "x"},
                  {"name": "Rodi", "iata": "RHO", "reason": "y"}]
    state = {"origin_iata": ["MXP"], "scout_candidates": candidates,
             "constraints": {"destination_hint": "mare tipo Grecia"},
             "selected_destination": "le destinazioni vanno bene così, passa alle offerte"}
    llm = SequenceLLM({"intent": "proceed"})  # only the intent classifier runs; NO re-generation
    out = await scout_node(state, llm)
    assert out["pending_question"] is None
    assert {d["iata"] for d in out["destinations"]} == {"HER", "RHO"}
    assert len(llm.calls) == 1


@pytest.mark.asyncio
async def test_scout_proceed_from_main_composer_message_searches_candidates():
    """Loop fix: the user typed 'passa alla ricerca delle offerte' in the MAIN composer (no card
    answer, so selected_destination is unset). With candidates already on the table, treat the
    latest message as the reply and proceed to search them rather than re-proposing forever."""
    candidates = [{"name": "Creta", "iata": "HER", "reason": "x"},
                  {"name": "Rodi", "iata": "RHO", "reason": "y"}]
    state = {"origin_iata": ["MXP"], "scout_candidates": candidates,
             "constraints": {"destination_hint": "mare tipo Grecia"},
             "messages": [{"role": "user", "content": "voglio andare al mare tipo Grecia"},
                          {"role": "assistant", "content": "Ho qualche destinazione adatta..."},
                          {"role": "user", "content": "Passa alla ricerca delle offerte"}]}
    llm = SequenceLLM({"intent": "proceed"})
    out = await scout_node(state, llm)
    assert out["pending_question"] is None
    assert {d["iata"] for d in out["destinations"]} == {"HER", "RHO"}
    assert len(llm.calls) == 1


@pytest.mark.asyncio
async def test_scout_main_composer_refine_still_reproposes():
    """A vague/refine instruction typed in the main composer must NOT proceed: it re-proposes,
    folding the typed guidance into the hint, so 'proceed' detection can't swallow real refines."""
    candidates = [{"name": "Creta", "iata": "HER", "reason": "x", "description": "d"}]
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19", "scout_candidates": candidates,
             "constraints": {"destination_hint": "mare tipo Grecia"},
             "messages": [{"role": "user", "content": "più verso la Spagna"}]}
    llm = SequenceLLM(
        {"intent": "refine"},
        {"destinations": [{"name": "Palma", "iata": "PMI", "reason": "Baleari", "description": "Mare."}]})
    out = await scout_node(state, llm)
    assert out["destinations"] == []
    assert out["pending_question"] is not None
    assert {o["value"] for o in out["pending_question"]["options"]} == {"PMI"}
    assert "Spagna" in llm.calls[1][1]  # typed guidance folded into the re-proposal


@pytest.mark.asyncio
async def test_scout_first_proposal_records_shown_destinations():
    """Every proposed batch is remembered in shown_destinations so later batches can avoid it."""
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19",
             "constraints": {"destination_hint": "mare tipo Grecia"}}
    llm = StubLLM({"destinations": [
        {"name": "Creta", "iata": "HER", "reason": "x", "description": "d"},
        {"name": "Rodi", "iata": "RHO", "reason": "y", "description": "d"}]})
    out = await scout_node(state, llm)
    assert {d["iata"] for d in out["shown_destinations"]} == {"HER", "RHO"}


@pytest.mark.asyncio
async def test_scout_generate_more_excludes_already_shown_even_without_selection():
    """'Genera altre opzioni' without picking anything must NOT return the same batch: the
    currently-shown candidates are excluded and the LLM is told to propose DIFFERENT ones."""
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19",
             "scout_candidates": [{"name": "Rodi", "iata": "RHO"}],
             "selected_destination": "", "selected_pool": [],
             "constraints": {"destination_hint": "mare tipo Grecia"},
             "generate_more": True}
    # LLM returns a batch that still includes the already-shown Rodi -> must be filtered out.
    llm = SequenceLLM({"destinations": [
        {"name": "Rodi", "iata": "RHO", "reason": "old", "description": "x"},
        {"name": "Kos", "iata": "KGS", "reason": "new", "description": "y"}]})
    out = await scout_node(state, llm)
    assert {c["iata"] for c in out["scout_candidates"]} == {"KGS"}      # Rodi excluded
    assert "Rodi" in llm.calls[0][1]                                    # LLM told to avoid Rodi
    assert any(d["iata"] == "RHO" for d in out["shown_destinations"])   # remembered as shown


@pytest.mark.asyncio
async def test_scout_generate_more_excludes_destinations_shown_in_prior_turns():
    """Repeated 'Genera altre opzioni' keeps excluding everything shown in earlier turns too."""
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19",
             "scout_candidates": [{"name": "Kos", "iata": "KGS"}],
             "shown_destinations": [{"name": "Rodi", "iata": "RHO"}],
             "selected_destination": "", "selected_pool": [],
             "constraints": {"destination_hint": "mare tipo Grecia"},
             "generate_more": True}
    llm = SequenceLLM({"destinations": [
        {"name": "Rodi", "iata": "RHO", "reason": "x", "description": "x"},
        {"name": "Kos", "iata": "KGS", "reason": "y", "description": "y"},
        {"name": "Naxos", "iata": "JNX", "reason": "z", "description": "z"}]})
    out = await scout_node(state, llm)
    assert {c["iata"] for c in out["scout_candidates"]} == {"JNX"}
    prompt = llm.calls[0][1]
    assert "Rodi" in prompt and "Kos" in prompt


@pytest.mark.asyncio
async def test_scout_generate_more_folds_refine_text_into_hint():
    """Item 3: free text typed alongside picks guides the next batch — the picks are saved to the
    pool and the typed guidance is folded into the hint that drives the fresh proposals."""
    llm = SequenceLLM({"destinations": [{"name": "Atene", "iata": "ATH",
                                         "reason": "r", "description": "d"}]})
    state = {"origin_iata": ["MXP"], "date_from": "2026-08-19",
             "scout_candidates": [{"name": "Lisbona", "iata": "LIS"}],
             "selected_destination": "LIS", "selected_pool": [], "generate_more": True,
             "refine_text": "più verso la Grecia", "constraints": {"destination_hint": "mare"}}
    out = await scout_node(state, llm)
    assert out.get("pending_question") is not None
    assert any(d["iata"] == "LIS" for d in out["selected_pool"])  # pick saved
    assert llm.calls and "Grecia" in llm.calls[0][1]              # guidance reached _generate


@pytest.mark.asyncio
async def test_scout_trim_answer_resolves_against_pool_not_only_candidates():
    """Trim-loop fix: the 'keep exactly 5' answer lists POOL entries (older batches). Matching
    it against the current candidates batch only always missed, the pool stayed over-full and
    the trim question re-appeared forever. The picks must resolve against the pool and REPLACE it."""
    pool = [{"name": f"P{i}", "iata": f"PP{i}"} for i in range(6)]
    state = {"scout_candidates": [{"name": "X", "iata": "XXX"}],  # fresh batch, no pool overlap
             "selected_pool": pool,
             "selected_destination": "PP0,PP1,PP2,PP3,PP4"}
    out = await scout_node(state, SequenceLLM())  # exact picks: no LLM call needed
    assert out.get("pending_question") is None
    assert [d["iata"] for d in out["destinations"]] == ["PP0", "PP1", "PP2", "PP3", "PP4"]
    assert out["selected_pool"] == []  # episode closed


@pytest.mark.asyncio
async def test_scout_trim_question_still_asked_when_pool_overfull():
    pool = [{"name": f"P{i}", "iata": f"PP{i}"} for i in range(6)]
    state = {"scout_candidates": [], "selected_pool": pool, "selected_destination": None}
    out = await scout_node(state, SequenceLLM())
    assert out["pending_question"] is not None
    assert len(out["pending_question"]["options"]) == 6
    assert out["scout_rounds"] == 1


@pytest.mark.asyncio
async def test_scout_generate_more_stops_after_max_rounds():
    """Anti-loop guard: after MAX_PROPOSAL_ROUNDS proposal rounds, 'genera altre opzioni'
    stops re-asking and searches the best destinations on the table."""
    from app.agent.nodes.scout import MAX_PROPOSAL_ROUNDS
    state = {"scout_candidates": [{"name": "A", "iata": "AAA"}],
             "selected_pool": [{"name": "B", "iata": "BBB"}],
             "generate_more": True, "scout_rounds": MAX_PROPOSAL_ROUNDS}
    out = await scout_node(state, SequenceLLM())  # no LLM needed: proceeds directly
    assert out.get("pending_question") is None
    assert [d["iata"] for d in out["destinations"]] == ["BBB"]  # pool wins over candidates


@pytest.mark.asyncio
async def test_scout_refine_stops_after_max_rounds():
    from app.agent.nodes.scout import MAX_PROPOSAL_ROUNDS
    candidates = [{"name": "A", "iata": "AAA"}, {"name": "B", "iata": "BBB"}]
    state = {"scout_candidates": candidates, "selected_destination": "qualcosa di diverso",
             "scout_rounds": MAX_PROPOSAL_ROUNDS}
    # Intent classifier says refine -> guard must proceed with the candidates instead of re-asking.
    out = await scout_node(state, SequenceLLM({"intent": "refine"}))
    assert out.get("pending_question") is None
    assert [d["iata"] for d in out["destinations"]] == ["AAA", "BBB"]


class FollowupLLM:
    """complete_json answers the follow-up classifier; complete_text the chat reply."""
    def __init__(self, intent, extra_json=None):
        self.intent = intent; self.extra = list(extra_json or []); self.json_calls = []
    async def complete_json(self, system, user):
        self.json_calls.append((system, user))
        if len(self.json_calls) == 1:
            return {"intent": self.intent}
        return self.extra.pop(0) if self.extra else {}
    async def complete_text(self, system, user):
        return "Con piacere! Fammi sapere se vuoi aggiornare la ricerca."


@pytest.mark.asyncio
async def test_scout_followup_keep_researches_committed_destinations():
    """After a completed search, a parameter tweak ('sposta a settembre') re-searches the SAME
    destinations with the updated brief instead of re-proposing or asking again."""
    committed = [{"name": "Atene", "iata": "ATH"}]
    state = {"destinations": committed, "scout_candidates": [], "selected_pool": [],
             "messages": [{"role": "user", "content": "sposta tutto a settembre"}]}
    out = await scout_node(state, FollowupLLM("keep"))
    assert out.get("pending_question") is None
    assert out["destinations"] == committed


@pytest.mark.asyncio
async def test_scout_followup_chat_replies_without_searching():
    """'grazie' after results must NOT re-run the search pipeline: short reply, no cards."""
    committed = [{"name": "Atene", "iata": "ATH"}]
    state = {"destinations": committed, "scout_candidates": [], "selected_pool": [],
             "messages": [{"role": "user", "content": "grazie mille!"}]}
    out = await scout_node(state, FollowupLLM("chat"))
    assert out["destinations"] == []
    assert out["ranked"] == []
    assert out.get("pending_question") is None
    assert out["final_message"]


@pytest.mark.asyncio
async def test_scout_followup_change_starts_new_proposal_round():
    """A new idea after results ('qualcosa in Grecia') starts a fresh proposal round."""
    committed = [{"name": "Tenerife", "iata": "TFS"}]
    state = {"destinations": committed, "scout_candidates": [], "selected_pool": [],
             "origin_iata": ["MXP"], "date_from": "2026-08-16",
             "constraints": {"destination_hint": "Canarie"},
             "messages": [{"role": "user", "content": "invece qualcosa in Grecia?"}]}
    llm = FollowupLLM("change", extra_json=[
        {"intent": "refine"},  # inner intent classifier on the free text
        {"destinations": [{"name": "Creta", "iata": "HER", "reason": "mare", "description": "x"},
                          {"name": "Rodi", "iata": "RHO", "reason": "mare", "description": "y"}]}])
    out = await scout_node(state, llm)
    assert out["pending_question"] is not None
    assert {d["iata"] for d in out["scout_candidates"]} == {"HER", "RHO"}
    assert out["destinations"] == []
