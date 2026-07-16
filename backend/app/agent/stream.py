"""SSE event adapter over the LangGraph stream."""

from typing import AsyncIterator

LABELS = {
    "intake": "Analizzo la tua richiesta",
    "scout": "Cerco le destinazioni migliori",
    "flight": "Cerco i voli",
    "hotel": "Cerco gli hotel",
    "package": "Cerco i pacchetti volo+hotel",
    "optimizer": "Confronto prezzi e budget",
    "presenter": "Preparo le proposte",
}


async def run_graph_events(graph, state, thread_id) -> AsyncIterator[dict]:
    """
    Async generator that drives a compiled LangGraph and yields SSE contract event dicts.

    Events:
    - agent_step (running+done) per executed node
    - question (if pending_question is present, stops here)
    - package (one per ranked card)
    - message (final message)
    - done (final marker)

    Args:
        graph: Compiled LangGraph with astream() and aget_state() methods.
        state: Initial state dict.
        thread_id: Thread ID for the LangGraph config.

    Yields:
        Event dicts matching the SSE contract.
    """
    config = {"configurable": {"thread_id": thread_id}}

    # Stream updates from the graph.
    async for update in graph.astream(state, config, stream_mode="updates"):
        for node, _ in update.items():
            label = LABELS.get(node, node)
            yield {"type": "agent_step", "agent": node, "status": "running", "label": label}
            yield {"type": "agent_step", "agent": node, "status": "done", "label": label}

    # Get final state.
    snap = await graph.aget_state(config)
    values = snap.values

    # Emit the extracted brief snapshot (also on question turns so the panel fills).
    constraints = values.get("constraints") or {}
    yield {
        "type": "brief",
        "data": {
            "destination_hint": constraints.get("destination_hint"),
            "date_from": values.get("date_from"),
            "date_to": values.get("date_to"),
            "window_from": values.get("window_from"),
            "window_to": values.get("window_to"),
            "trip_nights": values.get("trip_nights"),
            "dates_flexible": bool(values.get("dates_flexible")),
            "adults": values.get("adults"),
            "children_ages": values.get("children_ages") or [],
            "budget_per_person": values.get("budget_per_person"),
            "currency": values.get("currency") or "EUR",
            "min_stars": values.get("min_stars"),
            "preferred_hotels": values.get("preferred_hotels") or [],
            "origin_iata": values.get("origin_iata") or [],
            "search_mode": values.get("search_mode") or "flight_hotel",
            "accommodation_type": values.get("accommodation_type") or "both",
            "accommodation_area": values.get("accommodation_area"),
        },
    }

    # Check for pending question (stops here if present).
    if values.get("pending_question"):
        yield values["pending_question"]
        yield {"type": "done"}
        return

    # Emit packages (ranked cards).
    for card in values.get("ranked", []):
        yield {"type": "package", "data": card}

    # Emit final message if present.
    if values.get("final_message"):
        yield {"type": "message", "content": values["final_message"]}

    # Final marker.
    yield {"type": "done"}
