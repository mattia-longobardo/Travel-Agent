"""Candidate-period enumeration for flexible-date trips.

When the user gives a wide window ("le ultime due settimane di agosto") but a shorter
trip duration ("una settimana"), each destination should be priced across a few
candidate periods inside the window so the optimizer can pick the cheapest one *per
destination*. We cap the number of probes to keep MCP call volume bounded (decision:
3-4 slots per window).
"""
from datetime import date, timedelta

MAX_SLOTS = 4


def _parse(d: str | None) -> date | None:
    try:
        return date.fromisoformat(d) if d else None
    except (TypeError, ValueError):
        return None


def enumerate_slots(window_from: str | None, window_to: str | None,
                    nights: int | None, max_slots: int = MAX_SLOTS) -> list[tuple[str, str]]:
    """Return up to ``max_slots`` (date_from, date_to) ISO pairs of ``nights`` length
    inside [window_from, window_to].

    Falls back to a single slot when the window is missing, invalid, or not wider than
    the trip itself — so non-flexible searches behave exactly as before.
    """
    n = max(int(nights or 0), 1)
    wf, wt = _parse(window_from), _parse(window_to)
    if wf is None:
        return []
    if wt is None or (wt - wf).days <= n:
        # Window unknown or no slack: a single slot starting at window_from.
        return [(wf.isoformat(), (wf + timedelta(days=n)).isoformat())]

    latest_start = wt - timedelta(days=n)
    span = (latest_start - wf).days  # > 0 here
    count = min(max_slots, span + 1)
    if count <= 1:
        return [(wf.isoformat(), (wf + timedelta(days=n)).isoformat())]

    slots: list[tuple[str, str]] = []
    seen: set[str] = set()
    for i in range(count):
        # Evenly spaced start dates across the window, endpoints included.
        offset = round(span * i / (count - 1))
        start = wf + timedelta(days=offset)
        key = start.isoformat()
        if key in seen:
            continue
        seen.add(key)
        slots.append((key, (start + timedelta(days=n)).isoformat()))
    return slots


def slots_for_state(state: dict, max_slots: int = MAX_SLOTS) -> list[tuple[str, str]]:
    """Candidate (date_from, date_to) periods to probe for the given trip state.

    Only fans out when the user left the dates flexible *and* the window is wider than the
    trip; otherwise a single slot reproduces the original single-search behaviour.
    """
    date_from, date_to = state.get("date_from"), state.get("date_to")
    if not state.get("dates_flexible"):
        if date_from:
            return [(date_from, date_to or "")]
        return []
    window_from = state.get("window_from") or date_from
    window_to = state.get("window_to") or date_to
    nights = state.get("trip_nights")
    slots = enumerate_slots(window_from, window_to, nights, max_slots=max_slots)
    if slots:
        return slots
    return [(date_from, date_to or "")] if date_from else []
