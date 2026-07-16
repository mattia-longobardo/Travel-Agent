import asyncio
import json
from app.agent.currency import EUR, is_eur_offer
from app.agent.price import parse_price
from app.agent.search import CONCURRENCY, bounded_call
from app.agent.slots import slots_for_state
from app.agent.tool_perimeters import NS

SEARCH = NS + "search_flights"


def _parse(raw: str) -> tuple[object, list[dict]]:
    try:
        data = json.loads(raw)
    except Exception:
        return None, []
    if isinstance(data, dict):
        items = data.get("flights") or data.get("results") or []
        return data, (items if isinstance(items, list) else [])
    return data, (data if isinstance(data, list) else [])


def _items(raw: str) -> list[dict]:
    return _parse(raw)[1]


def _total(item: dict) -> float | None:
    if item.get("price_amount") is not None:
        v = parse_price(item["price_amount"])
        return round(v / 100, 2) if v is not None else None
    if item.get("price_cents") is not None:
        v = parse_price(item["price_cents"])
        return round(v / 100, 2) if v is not None else None
    return parse_price(item.get("price"))


def normalize_flights(raw: str, adults: int = 1, departure_iata: str | None = None) -> list[dict]:
    """lastminute returns the flight price as the TOTAL for the party; divide by adults.

    ``departure_iata`` (when given) tags each offer with the origin it was searched from, so
    the optimizer can pick the cheapest origin and carry it onto the card.
    """
    adults = max(adults or 1, 1)
    data, items = _parse(raw)
    out = []
    for it in items:
        if not is_eur_offer(it, data):
            continue
        total = _total(it)
        pp = round(total / adults, 2) if total is not None else None
        summary = it.get("summary") or it.get("outbound") or ""
        if it.get("return"):
            summary = f"{summary} | {it['return']}".strip(" |")
        out.append({"price_per_person": pp,
                    "currency": EUR,
                    "airline": it.get("airline") or it.get("carrier"),
                    "summary": summary,
                    "departure_iata": departure_iata,
                    "deeplink": it.get("deeplink"),
                    "pricing_id": it.get("pricing_id") or it.get("carrier_id")})
    return [f for f in out if f["price_per_person"] is not None]


async def flight_node(state, llm=None, mcp=None) -> dict:
    flights: dict[str, list[dict]] = {}
    if mcp is None:
        return {"flights": flights}
    origins = state.get("origin_iata") or ["MXP"]
    adults = state.get("adults", 1) or 1
    slots = slots_for_state(state)
    sem = asyncio.Semaphore(CONCURRENCY)
    jobs: list[tuple] = []  # (dest_iata, date_from, date_to, origin, coroutine)
    for dest in state.get("destinations", []):
        iata = dest["iata"]
        flights[iata] = []
        for date_from, date_to in slots:
            for origin in origins:
                jobs.append((iata, date_from, date_to, origin, bounded_call(
                    mcp, SEARCH, {"departure": origin, "arrival": iata,
                                  "start_date": date_from, "end_date": date_to or "",
                                  "adults": adults,
                                  # Force the Italian lastminute storefront. Without this the
                                  # MCP defaults to English and emits lastminute.ie deeplinks,
                                  # which can reopen the offer in GBP despite an EUR result.
                                  "language": "it"}, sem)))
    raws = await asyncio.gather(*(j[-1] for j in jobs))
    for (iata, date_from, date_to, origin, _), raw in zip(jobs, raws):
        for o in normalize_flights(raw, adults, departure_iata=origin):
            o["date_from"], o["date_to"] = date_from, date_to
            flights[iata].append(o)
    return {"flights": flights}
