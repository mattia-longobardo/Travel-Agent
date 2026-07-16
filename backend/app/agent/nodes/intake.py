from datetime import date
from app.agent.geo import airports_within
from app.agent.price import parse_price


def _system_prompt(today: str) -> str:
    return (
        f"Sei l'agente di Intake di un assistente di viaggio. Oggi è {today}. "
        "Estrai dalla richiesta dell'utente un brief JSON con i campi: "
        "date_from (YYYY-MM-DD), date_to (YYYY-MM-DD), dates_flexible (bool), "
        "window_from (YYYY-MM-DD|null), window_to (YYYY-MM-DD|null), nights (int|null), "
        "adults (int), children_ages (list[int]), budget_per_person (float|null in EUR), "
        "min_stars (int|null), "
        "preferred_hotels (list[str]: nomi di hotel SPECIFICI citati dall'utente, [] se nessuno), "
        "no_flight (bool: true se l'utente vuole viaggiare SENZA aereo — in auto, treno, "
        "on the road, via terra — altrimenti false), "
        "search_mode (str: 'hotel_only' se l'utente vuole SOLO l'alloggio/hotel — è già sul "
        "posto, ha già il volo, o viaggia via terra; 'flight_only' se vuole SOLO il volo — "
        "ha già dove dormire o cerca soltanto biglietti aerei; altrimenti 'flight_hotel'. "
        "Usa l'indicazione PIÙ RECENTE dell'utente se cambia idea), "
        "accommodation_type (str: 'hotel' se vuole solo hotel/resort, 'home' se vuole solo "
        "case/appartamenti/affitti brevi, 'both' se accetta entrambi o non specifica), "
        "accommodation_area (str|null: quartiere, zona o località SPECIFICA in cui vuole "
        "l'alloggio, es. 'Trastevere', 'Costa Adeje', 'centro storico'; non confonderla con "
        "la città/destinazione generale. Usa null se non è indicata e stringa vuota se "
        "l'utente annulla esplicitamente una zona scelta in precedenza), "
        "destination_hint (str, anche vago). "
        "Se l'utente nomina uno o più hotel precisi (es. 'l'hotel Anantara Qasr Al Sareb'), "
        "mettili in preferred_hotels. NON inventarli. "
        "Risolvi SEMPRE le espressioni temporali relative o in linguaggio naturale in date "
        "ASSOLUTE nel futuro rispetto a oggi; se l'anno non è indicato usa la prossima occorrenza. "
        "Distingui la DURATA del viaggio (nights) dalla FINESTRA in cui può cadere "
        "(window_from..window_to). Se l'utente indica una finestra ampia (es. 'ultime due "
        "settimane di agosto', 'a settembre', 'in estate') senza specificare quante notti, NON "
        "usare l'intero intervallo come durata: imposta nights a una durata tipica di 7, "
        "window_from/window_to ALL'INTERA finestra, date_from all'inizio della finestra e date_to "
        "nights giorni dopo, e dates_flexible=true. Se invece la durata è esplicita ('10 giorni', "
        "'un weekend', 'due settimane di vacanza') usala come nights. Esempio: 'una settimana nelle "
        "ultime due settimane di agosto' → window_from 2026-08-18, window_to 2026-08-31, nights 7, "
        "date_from 2026-08-18, date_to 2026-08-25, dates_flexible=true. Quando le date sono fisse, "
        "window_from=date_from e window_to=date_to. Imposta date_from a null SOLO se non c'è alcun "
        "riferimento temporale. NON inventare il budget: se non indicato, budget_per_person=null."
    )

# Domande pre-compilate per i campi obbligatori mancanti
PRECOMPILED = {
    "trip_nights": {
        "text": "Quante notti vuoi stare?",
        "options": [{"label": "Weekend (2)", "value": 2}, {"label": "5 notti", "value": 5},
                    {"label": "1 settimana", "value": 7}, {"label": "10 notti", "value": 10},
                    {"label": "2 settimane", "value": 14}],
    },
    "budget_per_person": {
        "text": "Qual è il budget a persona (volo+hotel)?",
        "options": [{"label": "≤ 500 €", "value": 500}, {"label": "≤ 750 €", "value": 750},
                    {"label": "≤ 1000 €", "value": 1000}, {"label": "≤ 1500 €", "value": 1500}],
    },
    "date_from": {
        "text": "In che periodo vuoi partire?",
        "options": [{"label": "Seconda metà agosto", "value": "2026-08-16"},
                    {"label": "Prima metà settembre", "value": "2026-09-01"},
                    {"label": "Ponte di ottobre", "value": "2026-10-31"}],
    },
    "adults": {
        "text": "In quanti viaggiate?",
        "options": [{"label": "1", "value": 1}, {"label": "2", "value": 2},
                    {"label": "3", "value": 3}, {"label": "4", "value": 4}],
    },
}
REQUIRED = ["trip_nights", "date_from", "budget_per_person"]

VALID_MODES = {"flight_hotel", "hotel_only", "flight_only"}
VALID_ACCOMMODATION_TYPES = {"hotel", "home", "both"}
# What the per-person budget covers, per search mode (used in the budget question text).
_BUDGET_SCOPE = {"flight_hotel": "volo+hotel", "hotel_only": "solo alloggio", "flight_only": "solo volo"}

# Domanda opzionale sulla categoria hotel. Le stelle minime sono l'UNICA preferenza
# realmente filtrabile dalla sorgente (lastminute): trattamento e piscina non sono
# parametri di ricerca, quindi non vengono chiesti. Chiesta una sola volta dopo i campi
# obbligatori; la risposta torna come prefill["min_stars"] e imposta direttamente min_stars.
STARS_QUESTION = {
    "type": "question",
    "id": "min_stars",
    "allow_free_text": True,
    "text": "Che categoria di hotel preferisci?",
    "options": [
        {"label": "Indifferente", "value": 0},
        {"label": "3★ o più", "value": 3},
        {"label": "4★ o più", "value": 4},
        {"label": "5★", "value": 5},
    ],
}


def _nights(explicit, date_from: str | None, date_to: str | None) -> int:
    """Trip duration in nights: explicit value, else derived from date span, else 7."""
    try:
        if explicit:
            return max(int(explicit), 1)
    except (TypeError, ValueError):
        pass
    try:
        d1 = date.fromisoformat(date_from); d2 = date.fromisoformat(date_to)
        return max((d2 - d1).days, 1)
    except (TypeError, ValueError):
        return 7

async def intake_node(state, llm) -> dict:
    user_text = " ".join(m["content"] for m in state.get("messages", []) if m["role"] == "user")
    brief = await llm.complete_json(_system_prompt(date.today().isoformat()), user_text)

    # The graph re-enters intake on EVERY turn, and the LLM re-extracts the brief from the
    # concatenated user text where a precompiled answer (a bare "7") is ambiguous and often
    # comes back null. A null re-extraction must NOT wipe a slot the user already answered
    # (it lives in the checkpointed state) — otherwise the question gets asked again. So for
    # each accumulated slot prefer a fresh non-null value, else fall back to the prior state.
    def keep(new, key):
        return new if new is not None else state.get(key)

    prior_constraints = state.get("constraints") or {}
    date_from = keep(brief.get("date_from"), "date_from")
    date_to = keep(brief.get("date_to"), "date_to")
    prefill = state.get("prefill") or {}

    # Explicit request prefill wins over LLM extraction; otherwise the latest valid extracted
    # mode wins (the user can change idea mid-chat). Overland trips are hotel-only by definition.
    # Falls back to the prior mode, then to the full comparison.
    explicit_mode = prefill.get("search_mode")
    mode = explicit_mode or brief.get("search_mode")
    if mode not in VALID_MODES:
        mode = state.get("search_mode") if state.get("search_mode") in VALID_MODES else None
    no_flight = bool(brief.get("no_flight")) or bool(state.get("no_flight"))
    # A visible UI mode is authoritative. In particular, a stale checkpointed no_flight=True
    # must not trap a later explicit Solo volo / Volo+hotel selection in hotel-only mode.
    if explicit_mode in VALID_MODES and explicit_mode != "hotel_only":
        no_flight = False
    elif no_flight:
        mode = "hotel_only"
    mode = mode or "flight_hotel"

    accommodation_type = prefill.get("accommodation_type") or brief.get("accommodation_type")
    if accommodation_type not in VALID_ACCOMMODATION_TYPES:
        prior_accommodation_type = state.get("accommodation_type")
        accommodation_type = (
            prior_accommodation_type
            if prior_accommodation_type in VALID_ACCOMMODATION_TYPES else "both"
        )
    # A missing extraction must not erase an area already checkpointed on a later answer turn.
    # An explicitly empty string, on the other hand, lets the user remove the area constraint.
    extracted_area = brief.get("accommodation_area")
    if extracted_area is None:
        accommodation_area = state.get("accommodation_area")
    else:
        accommodation_area = str(extracted_area).strip() or None
    out: dict = {
        "date_from": date_from, "date_to": date_to,
        "window_from": brief.get("window_from") or state.get("window_from") or date_from,
        "window_to": brief.get("window_to") or state.get("window_to") or date_to,
        # Nullable when never provided (triggers the trip_nights question), but sticky once
        # answered so a later null re-extraction can't re-ask it.
        "trip_nights": keep(brief.get("nights"), "trip_nights"),
        "dates_flexible": bool(brief.get("dates_flexible")) or bool(state.get("dates_flexible")),
        "adults": brief.get("adults") or state.get("adults") or 1,
        "children_ages": brief.get("children_ages") or state.get("children_ages") or [],
        "budget_per_person": parse_price(keep(brief.get("budget_per_person"), "budget_per_person")),
        "currency": "EUR", "min_stars": keep(brief.get("min_stars"), "min_stars"),
        # A named specific hotel pins WHERE to stay (scout derives the destination); both slots
        # are sticky so a later null re-extraction can't wipe them.
        "preferred_hotels": brief.get("preferred_hotels") or state.get("preferred_hotels") or [],
        "no_flight": no_flight,
        "search_mode": mode,
        "accommodation_type": accommodation_type,
        "accommodation_area": accommodation_area,
        "preferences_asked": bool(state.get("preferences_asked")),
        "constraints": {
            "destination_hint": brief.get("destination_hint") or prior_constraints.get("destination_hint"),
        },
        # Per-turn UI flags: they arrive via prefill only on the turn the user actually used
        # them, but live in the checkpointed state. Reset them here on EVERY turn (prefill
        # re-sets them below when present) — otherwise a single "Genera altre opzioni" click
        # left generate_more=True forever and the scout re-proposed destinations on every
        # following turn instead of ever proceeding to the search (the reported loop).
        "generate_more": False,
        "refine_text": None,
    }
    coords = state.get("origin_coords")
    if coords:
        out["origin_iata"] = [a["iata"] for a in airports_within(coords[0], coords[1], 80.0)]
    for k, v in prefill.items():
        # These two fields were validated and applied above; do not let answer_to inject an
        # arbitrary value that bypasses their enums.
        if v is not None and k not in {"search_mode", "accommodation_type"}:
            out[k] = v
    missing = [f for f in REQUIRED if not out.get(f)]
    out["missing"] = missing
    if missing:
        # Required questions always take priority over the optional hotel-category one.
        field = missing[0]
        spec = PRECOMPILED[field]
        text = spec["text"]
        if field == "budget_per_person":
            # The budget scope depends on what we are actually searching for.
            text = f"Qual è il budget a persona ({_BUDGET_SCOPE[mode]})?"
        out["pending_question"] = {"type": "question", "id": field, "text": text,
                                   "options": spec["options"], "allow_free_text": True}
    elif (mode != "flight_only" and accommodation_type != "home"
          and not out["preferences_asked"] and not out.get("min_stars")):
        # All required fields satisfied and no hotel category volunteered: ask the
        # optional star-rating question exactly once (the only filterable preference).
        # Pointless for flight-only trips, where no hotel is searched.
        out["pending_question"] = dict(STARS_QUESTION)
        out["preferences_asked"] = True
    else:
        out["pending_question"] = None
    return out
