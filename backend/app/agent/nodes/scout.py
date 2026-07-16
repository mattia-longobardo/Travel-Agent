SYSTEM = (
    "Sei il Destination Advisor. Dato un punto di partenza (IATA), un periodo e un suggerimento "
    "anche vago (es. \"al mare come la Spagna, altre proposte?\" oppure \"qualcosa tipo le Azzorre\"), "
    "proponi DA 3 A 5 DESTINAZIONI CONCRETE a DISTANZA SIMILE dall'origine, coerenti per clima/stagione. "
    "Per ognuna includi: name, iata (codice IATA citta/aeroporto della destinazione), reason (perche e adatta), "
    "e description (1-2 frasi: com'e il posto e cosa farci). "
    "Rispondi SOLO JSON: "
    "{\"destinations\":[{\"name\":..,\"iata\":..,\"reason\":..,\"description\":..}]}."
)

# Resolve a destination the user has ALREADY named to its airport — the city itself, never
# similar/nearby alternatives. Kept distinct from SYSTEM (which proposes alternatives) so a
# concrete hint like "New York" can never come back as a neighbouring city like Boston.
RESOLVE_SYSTEM = (
    "L'utente ha indicato UNA destinazione precisa su cui vuole viaggiare. "
    "Restituisci ESATTAMENTE QUELLA destinazione — NON alternative, NON città simili o vicine — "
    "con il codice IATA dell'aeroporto principale che la serve. Se la città ha più aeroporti "
    "scegli quello principale per i voli di linea (es. New York→JFK, Londra→LHR, Milano→MXP, "
    "Tokyo→HND). Includi name, iata, reason e description (1-2 frasi: com'è il posto e cosa farci). "
    "Rispondi SOLO JSON {\"destinations\":[{\"name\":..,\"iata\":..,\"reason\":..,\"description\":..}]} "
    "con UNA SOLA destinazione: quella indicata."
)

INTENT_SYSTEM = (
    "L'utente ha ricevuto alcune proposte di destinazione e ha risposto liberamente. "
    "Classifica la risposta in UNO di tre intenti: "
    "'confirm' = indica UNA destinazione concreta su cui procedere "
    "(es. 'Atene', 'Creta', 'Santorini', 'la prima', 'Tenerife'); "
    "'proceed' = le proposte vanno bene COSÌ COME SONO e vuole passare alla ricerca SENZA "
    "sceglierne una o chiederne altre (es. 'vanno bene così', 'va bene così', 'procedi', "
    "'passa alla ricerca', 'cerca le offerte', 'ok così', 'sono tutte ok', "
    "'non voglio altre proposte', 'basta proposte'); "
    "'refine' = chiede ALTRE proposte o esprime una preferenza vaga/diversa "
    "(es. 'qualcosa come la Grecia', 'al mare tipo Spagna', 'non so', 'altre proposte', "
    "'piu economico', 'piu verso la Grecia'). "
    "Rispondi SOLO JSON {\"intent\":\"confirm\"|\"proceed\"|\"refine\"}. "
    "Nel dubbio, rispondi refine."
)

SPECIFIC_SYSTEM = (
    "L'utente ha indicato una destinazione. È UNA destinazione concreta e singola su cui "
    "procedere (es. 'Tenerife', 'Atene', 'Maldive'), oppure è VAGA/MULTIPLA "
    "(es. 'al mare', 'tipo Grecia', 'qualcosa di caldo', 'non so')? "
    "Rispondi SOLO JSON {\"specific\": true|false}. Nel dubbio: false."
)

# id of the destination-choice question; the answer comes back as prefill[selected_destination].
QUESTION_ID = "selected_destination"

FOLLOWUP_SYSTEM = (
    "L'utente ha già ricevuto i risultati di una ricerca di viaggio per le destinazioni "
    "indicate e ora ha scritto un nuovo messaggio. Classifica l'intento in UNO di tre valori: "
    "'keep' = vuole rifare o aggiornare la ricerca sulle STESSE destinazioni "
    "(cambia date, budget, notti, numero di persone, categoria hotel, oppure chiede di "
    "ricontrollare/aggiornare i prezzi o di cercare di nuovo); "
    "'change' = vuole destinazioni DIVERSE o nuove proposte "
    "(nomina un altro posto, chiede altre idee o alternative); "
    "'chat' = commento o domanda che NON richiede una nuova ricerca "
    "(ringraziamenti, saluti, domande sulle proposte già mostrate, es. 'grazie', "
    "'qual è la migliore?', 'che tempo fa lì?'). "
    "Rispondi SOLO JSON {\"intent\":\"keep\"|\"change\"|\"chat\"}. Nel dubbio: keep."
)

CHAT_SYSTEM = (
    "Sei un assistente di viaggio italiano. L'utente ha già ricevuto delle proposte di viaggio "
    "(le vede come card nella chat) e ora scrive un messaggio che non richiede una nuova "
    "ricerca. Rispondi in modo breve, cordiale e utile (1-3 frasi), senza inventare prezzi, "
    "disponibilità o dettagli che non conosci."
)

HOTEL_DEST_SYSTEM = (
    "Per ciascun hotel indicato restituisci la destinazione di ricerca: name (città) e iata "
    "(codice IATA dell'aeroporto più vicino servito). Rispondi SOLO JSON "
    "{\"destinations\":[{\"name\":..,\"iata\":..}]}. Massimo una destinazione per hotel."
)


async def _destinations_for_hotels(llm, hotels: list[str]) -> list[dict]:
    user = "Hotel: " + "; ".join(hotels)
    data = await llm.complete_json(HOTEL_DEST_SYSTEM, user)
    out = []
    for d in (data.get("destinations") or [])[:4]:
        if d.get("iata"):
            out.append({"name": d.get("name") or d["iata"], "iata": d["iata"],
                        "reason": "", "description": ""})
    return out


def _option_label(d: dict) -> str:
    name, reason = d.get("name") or d.get("iata") or "?", (d.get("reason") or "").strip()
    return f"{name} — {reason}" if reason else name


def _question(candidates: list[dict]) -> dict:
    return {
        "type": "question", "id": QUESTION_ID,
        "text": ("Ho qualche destinazione adatta: scegline una o più da confrontare per te "
                 "(puoi sceglierne più di una). Oppure dimmi un'altra idea, es. «più verso la Grecia»."),
        "multi_select": True,
        "options": [
            {"label": _option_label(d), "value": d.get("iata") or d.get("name"),
             "description": d.get("description")}
            for d in candidates
        ],
        "allow_free_text": True,
    }


def _trim_question(pool: list[dict]) -> dict:
    """Like `_question`, but for an over-full accumulated pool: ask the user to keep exactly 5
    among the destinations they already selected (multi_select over the pool)."""
    return {
        "type": "question", "id": QUESTION_ID,
        "text": ("Hai selezionato più di 5 destinazioni. Scegline esattamente 5 tra quelle "
                 "che hai già messo da parte, così le confronto per te."),
        "multi_select": True,
        "options": [
            {"label": _option_label(d), "value": d.get("iata") or d.get("name"),
             "description": d.get("description")}
            for d in pool
        ],
        "allow_free_text": True,
    }


def _resolve(selected: str, candidates: list[dict]) -> list[dict]:
    """Match the user's pick (iata or name, possibly comma-separated) to scouted candidates."""
    wanted = [s.strip().lower() for s in str(selected).split(",") if s.strip()]
    out: list[dict] = []
    for w in wanted:
        for c in candidates:
            if w in {(c.get("iata") or "").lower(), (c.get("name") or "").lower()}:
                if c not in out:
                    out.append(c)
                break
    return out


# Cap on how many already-shown destinations we remember / feed back to the model, so the
# avoid-list (and the prompt) can't grow without bound across many "Genera altre opzioni" clicks.
_SHOWN_CAP = 24

# Hard stop for the propose→refine→propose conversation loop: after this many proposal rounds
# without a confirmed pick, the scout stops asking and searches the best destinations it has
# (accumulated pool, else current candidates). The avoid-list alone cannot guarantee progress —
# once it saturates (_SHOWN_CAP) the model legitimately re-proposes old destinations and the
# question would re-appear forever.
MAX_PROPOSAL_ROUNDS = 4

# State keys reset when a destination episode closes (a search actually starts). Without this,
# stale candidates/picks made ANY later message re-match an old option and re-run the search.
_EPISODE_RESET = {"scout_candidates": [], "selected_pool": [],
                  "selected_destination": None, "scout_rounds": 0}


def _proceed(destinations: list[dict]) -> dict:
    """Close the proposal episode and hand `destinations` to the search fan-out."""
    return {"destinations": destinations, "pending_question": None, **_EPISODE_RESET}


async def _classify_followup(llm, committed: list[dict], message: str) -> str:
    """After a completed search: keep (re-search same destinations), change (new proposals),
    chat (conversational reply, no search). Nel dubbio / errore -> keep."""
    if not (message or "").strip():
        return "keep"
    names = ", ".join(_label_of(d) for d in committed if _label_of(d)) or "(nessuna)"
    user = f"Destinazioni della ricerca precedente: {names}. Nuovo messaggio: \"{message}\"."
    try:
        data = await llm.complete_json(FOLLOWUP_SYSTEM, user)
        intent = str((data or {}).get("intent") or "").strip().lower()
    except Exception:
        intent = ""
    return intent if intent in {"keep", "change", "chat"} else "keep"


async def _chat_reply(llm, committed: list[dict], message: str) -> str:
    names = ", ".join(_label_of(d) for d in committed if _label_of(d))
    user = (f"Proposte già mostrate per: {names or 'nessuna destinazione'}. "
            f"Messaggio dell'utente: \"{message}\".")
    try:
        reply = (await llm.complete_text(CHAT_SYSTEM, user) or "").strip()
    except Exception:
        reply = ""
    return reply or ("Va bene! Se vuoi posso aggiornare la ricerca (date, budget, destinazioni): "
                     "dimmi pure cosa cambiare.")


def _label_of(d: dict) -> str:
    return d.get("name") or d.get("iata") or ""


def _merge_shown(*groups: list[dict]) -> list[dict]:
    """Union of destination dicts across groups, de-duplicated by iata (fallback name),
    capped to the most recent _SHOWN_CAP so the avoid-list stays bounded."""
    out: list[dict] = []
    seen: set[str] = set()
    for g in groups:
        for d in g or []:
            key = ((d.get("iata") or d.get("name") or "")).lower()
            if key and key not in seen:
                seen.add(key)
                out.append({"name": d.get("name"), "iata": d.get("iata")})
    return out[-_SHOWN_CAP:]


async def _generate(llm, state, web_search, exclude: list[dict] | None = None) -> list[dict]:
    hint = (state.get("constraints") or {}).get("destination_hint") or ""
    origin = ", ".join(state.get("origin_iata") or [])
    context = ""
    if web_search and hint:
        context = "\nContesto dal web:\n" + (web_search(f"destinazioni simili a {hint} da {origin} in agosto") or "")
    # Tell the model which destinations were already proposed so each fresh batch is genuinely
    # DIFFERENT (otherwise the same canonical picks come back every time and the list looks stuck).
    avoid = ""
    names = [n for n in (_label_of(d) for d in (exclude or [])) if n]
    if names:
        avoid = (" NON riproporre queste destinazioni già mostrate (proponine di DIVERSE, anche "
                 "meno ovvie ma sempre coerenti per distanza/clima/stagione): " + ", ".join(names) + ".")
    user = f"Origine: {origin}. Periodo: {state.get('date_from')}. Suggerimento: {hint}.{avoid}{context}"
    data = await llm.complete_json(SYSTEM, user)
    return (data.get("destinations") or [])[:5]


async def _resolve_concrete(llm, hint: str) -> list[dict]:
    """Map a single NAMED destination (e.g. 'New York') to its airport(s) — the destination
    itself, never similar alternatives. Used when we already know WHERE the user wants to go,
    so it must NOT go through `_generate`'s 'propose alternatives at similar distance' prompt."""
    if not (hint or "").strip():
        return []
    try:
        data = await llm.complete_json(RESOLVE_SYSTEM, str(hint))
    except Exception:
        return []
    return (data.get("destinations") or [])


def _drop_excluded(batch: list[dict], exclude: list[dict]) -> list[dict]:
    """Filter out any destination whose iata is in `exclude`. If filtering empties the batch
    (the model only returned repeats), keep the raw batch — an empty proposal card is worse."""
    bad = {(d.get("iata") or "").lower() for d in exclude if d.get("iata")}
    kept = [c for c in batch if (c.get("iata") or "").lower() not in bad]
    return kept or batch


async def _hint_is_specific(llm, hint: str) -> bool:
    """True only when the raw intake hint denotes a single concrete destination.
    Nel dubbio (vague/multiple/empty/error) -> False, so we never wrongly skip the question."""
    if not (hint or "").strip():
        return False
    try:
        data = await llm.complete_json(SPECIFIC_SYSTEM, hint)
        return bool((data or {}).get("specific"))
    except Exception:
        return False


def _latest_user_message(state) -> str:
    """The most recent user turn — used when the user replies in the MAIN composer instead of
    the destination card, so the reply never arrives as `selected_destination`."""
    for m in reversed(state.get("messages") or []):
        if m.get("role") == "user":
            return (m.get("content") or "").strip()
    return ""


async def _classify_intent(llm, selected, candidates: list[dict], hint: str) -> str:
    """confirm = commit to a concrete destination; proceed = keep the proposals as-is and search;
    refine = ask for other proposals / vague pref. Nel dubbio -> refine."""
    # Exact pick (clicked/typed an option) short-circuits — no LLM needed.
    if _resolve(selected, candidates):
        return "confirm"
    options = ", ".join((c.get("name") or c.get("iata") or "?") for c in candidates) or "(nessuna)"
    user = (f"Proposte precedenti: {options}. Preferenza accumulata: {hint}. "
            f"Risposta dell'utente: \"{selected}\".")
    try:
        data = await llm.complete_json(INTENT_SYSTEM, user)
        intent = str((data or {}).get("intent") or "").strip().lower()
    except Exception:
        intent = ""
    return intent if intent in {"confirm", "proceed", "refine"} else "refine"


async def scout_node(state, llm, web_search=None) -> dict:
    candidates = state.get("scout_candidates") or []
    selected = state.get("selected_destination")
    preferred = state.get("preferred_hotels") or []
    pool = list(state.get("selected_pool") or [])
    rounds = int(state.get("scout_rounds") or 0)

    # Follow-up turn after a COMPLETED search (episode closed: no candidates/picks pending,
    # destinations committed). Classify the new message instead of blindly re-searching or
    # re-proposing: parameter tweaks re-search the same destinations, a new idea starts a new
    # proposal round, chit-chat gets a short reply without burning a full search. Checked
    # before the named-hotels shortcut, which would otherwise re-search on every message.
    committed = state.get("destinations") or []
    if (committed and not candidates and not pool and not selected
            and not state.get("generate_more")):
        message = _latest_user_message(state)
        intent = await _classify_followup(llm, committed, message)
        if intent == "chat":
            reply = await _chat_reply(llm, committed, message)
            return {"destinations": [], "ranked": [], "pending_question": None,
                    "final_message": reply}
        if intent == "change":
            # Fall through to a fresh proposal round driven by the new message.
            selected = message or None
            candidates = []
        else:  # keep: re-run the search on the same destinations with the updated brief.
            return _proceed(committed)

    # The user already chose WHERE to stay (named hotels): derive the destination(s)
    # directly and search — never ask the destination question.
    if preferred and not selected and not candidates:
        chosen = await _destinations_for_hotels(llm, preferred)
        if chosen:
            return _proceed(chosen)

    # When a destination proposal is already on the table and the user replies in the MAIN
    # composer instead of the card, the reply never arrives as `selected_destination`. Treat the
    # latest chat message as that free-text reply so the intent logic (confirm/proceed/refine)
    # applies — otherwise a "passa alla ricerca / vanno bene così" would fall through to a fresh
    # proposal and the destination question would loop forever.
    if candidates and not selected and not state.get("generate_more"):
        selected = _latest_user_message(state) or None

    # Item 3: accumulate the user's picks across turns into selected_pool (dedup by iata).
    # Picks are matched against the CURRENT batch and the pool itself: the trim question
    # ("keep exactly 5") lists pool entries from OLDER batches, which a candidates-only match
    # would miss — the pool would stay over-full and the trim question would re-appear forever.
    newly = _resolve(selected or "", candidates + pool)
    if len(pool) > 5 and newly:
        # Answer to the trim question: the picks REPLACE the pool ("keep exactly these").
        pool = newly
    else:
        for d in newly:
            if all((d.get("iata") or "").lower() != (p.get("iata") or "").lower() for p in pool):
                pool.append(d)

    # Everything already proposed so far (this batch + earlier ones): fed to the model as an
    # avoid-list and filtered out of fresh batches so "Genera altre opzioni" / refine never
    # return the same destinations again.
    shown = _merge_shown(state.get("shown_destinations") or [], candidates)

    # "Genera altre opzioni": keep the accumulated pool and propose a FRESH batch that
    # excludes anything already pooled OR already shown, then ask again — unless the proposal
    # rounds are exhausted, in which case proceed with the best destinations on the table.
    if state.get("generate_more"):
        if rounds >= MAX_PROPOSAL_ROUNDS and (pool or candidates):
            return _proceed((pool or candidates)[:5])
        # Free text typed alongside the picks is guidance: fold it into the hint that drives
        # the fresh batch (e.g. picks + "più verso la Grecia").
        gen_state = state
        refine = (state.get("refine_text") or "").strip()
        if refine:
            base_hint = (state.get("constraints") or {}).get("destination_hint") or ""
            gen_state = dict(state)
            gen_state["constraints"] = {"destination_hint": (base_hint + " " + refine).strip()}
        avoid = _merge_shown(shown, pool)
        fresh = _drop_excluded(await _generate(llm, gen_state, web_search, exclude=avoid), avoid)
        return {"selected_pool": pool, "scout_candidates": fresh,
                "shown_destinations": _merge_shown(shown, fresh),
                "pending_question": _question(fresh), "destinations": [],
                "scout_rounds": rounds + 1}

    # No refine signal: finalize from the accumulated pool.
    #   ≤5 -> proceed to search those destinations (no question).
    #   >5 -> ask the user to keep exactly 5 among the ones already selected
    #         (rounds exhausted: stop asking and search the first 5).
    if pool:
        if len(pool) <= 5 or rounds >= MAX_PROPOSAL_ROUNDS:
            return _proceed(pool[:5])
        return {"selected_pool": pool, "destinations": [],
                "pending_question": _trim_question(pool), "scout_rounds": rounds + 1}

    # Turn 2+: the user has answered the choice question.
    if selected:
        chosen = _resolve(selected, candidates)
        if chosen:
            # Exact pick of a proposed option -> proceed to search.
            return _proceed(chosen)

        hint = (state.get("constraints") or {}).get("destination_hint") or ""
        intent = await _classify_intent(llm, selected, candidates, hint)

        if intent == "confirm":
            # Free-text confirmation of a named destination: resolve THAT city to its airport(s)
            # and search — never via _generate (which would propose similar/nearby cities).
            chosen = (await _resolve_concrete(llm, str(selected)))[:2]
            if chosen:
                return _proceed(chosen)

        if intent == "proceed" and candidates:
            # "Le proposte vanno bene così, procedi": exit the propose-loop and search the
            # destinations already on the table (capped at 5) instead of re-proposing.
            return _proceed(candidates[:5])

        if rounds >= MAX_PROPOSAL_ROUNDS and candidates:
            # Proposal rounds exhausted: stop refining and search what's on the table.
            return _proceed(candidates[:5])

        # Refine: re-propose up to 5 fresh described destinations reflecting the new preference,
        # excluding everything already shown so the new batch is actually different.
        combined = " ".join(p for p in [hint, str(selected)] if p).strip()
        refined = dict(state)
        refined["constraints"] = {"destination_hint": combined}
        avoid = _merge_shown(shown, pool)
        new_candidates = await _generate(llm, refined, web_search, exclude=avoid)
        if not new_candidates:
            # Never leave the user stuck: fall back to resolving the free text as a named
            # destination (the city itself, not similar alternatives).
            chosen = (await _resolve_concrete(llm, str(selected)))[:2]
            if chosen:
                return _proceed(chosen)
            return {"destinations": [], "ranked": [], "pending_question": None,
                    "final_message": ("Non ho trovato destinazioni adatte a questa richiesta: "
                                      "puoi darmi qualche indicazione in più (zona, clima, "
                                      "tipo di viaggio)?")}
        new_candidates = _drop_excluded(new_candidates, avoid)
        return {"destinations": [], "scout_candidates": new_candidates,
                "shown_destinations": _merge_shown(shown, new_candidates),
                "pending_question": _question(new_candidates), "scout_rounds": rounds + 1}

    # Turn 1, single concrete destination: resolve it directly and search — no proposal/question.
    hint = (state.get("constraints") or {}).get("destination_hint")
    if hint and not selected and not candidates and await _hint_is_specific(llm, hint):
        chosen = (await _resolve_concrete(llm, hint))[:1] or _resolve(hint, [])
        if chosen:
            return _proceed(chosen)

    # Turn 1: propose options and STOP so the user can choose (decision: always confirm).
    candidates = await _generate(llm, state, web_search, exclude=shown)
    if not candidates:
        return {"destinations": [], "ranked": [], "scout_candidates": [],
                "pending_question": None,
                "final_message": ("Non sono riuscito a proporre destinazioni per questa "
                                  "richiesta: puoi riformularla con qualche dettaglio in più?")}
    return {"destinations": [], "scout_candidates": candidates,
            "shown_destinations": _merge_shown(shown, candidates),
            "pending_question": _question(candidates), "scout_rounds": rounds + 1}
