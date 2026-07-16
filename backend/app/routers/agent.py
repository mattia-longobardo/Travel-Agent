import asyncio
import json
import re
import time
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session, SessionLocal
from app.deps import get_current_user, get_graph, get_openai
from app.chat_access import user_chat_permission
from app.config import get_settings
from app.models import Chat, Message, RunTelemetry, User
from app.chat_titles import DEFAULT_CHAT_TITLE, generate_chat_title
from app.agent import telemetry
from app.agent.stream import run_graph_events

router = APIRouter(prefix="/api/chats", tags=["agent"])

# Detached agent runs must outlive the client connection (the user may navigate away
# mid-run). We keep a strong reference to each background task here so it isn't
# garbage-collected before it finishes; a done-callback discards it.
_BACKGROUND_RUNS: set[asyncio.Task] = set()

# Active runs keyed by chat id so POST /{id}/stop can cancel the in-flight graph task.
# Process-local: the backend runs a single uvicorn process (see entrypoint.sh).
_ACTIVE_RUNS: dict[int, asyncio.Task] = {}

# Runs cancelled because a NEWER message superseded them (not a user Stop): they are
# discarded silently — no "interrotta" bubble, and run_active stays owned by the new run.
_SUPERSEDED: set[int] = set()

STOPPED_MESSAGE = "🛑 Ricerca interrotta. Scrivimi pure per riprovare o modificare la richiesta."

# SSE keep-alive: the agent pipeline has long silent gaps (slow MCP calls); without a
# periodic heartbeat a proxy (Cloudflare tunnel / Traefik / Next rewrite) idle-times-out
# and cuts the stream, so the UI appears "stuck". A comment line (": ...") is ignored by
# the EventSource/SSE parser on the client.
HEARTBEAT_SECS = 15
_AUTO_TITLE_PLACEHOLDERS = {DEFAULT_CHAT_TITLE, "Nuovo viaggio", ""}

# Hard ceiling on a single agent run. Search MCP calls have their own per-call timeout, but a
# pathological run (hung LLM call, runaway link-minting) must still terminate: past this the
# run is treated like a user stop, partial output discarded, so the chat never wedges forever.
RUN_TIMEOUT_SECS = 600


async def _title_from_first_message(first_message: str) -> str:
    settings = get_settings()
    client = get_openai() if settings.openai_api_key else None
    return await generate_chat_title(first_message, client, settings.openai_model)

class MessageIn(BaseModel):
    content: str
    coords: list[float] | None = None
    answer_to: str | None = None
    generate_more: bool = False
    refine_text: str = ""
    search_mode: Literal["flight_hotel", "hotel_only", "flight_only"] | None = None
    accommodation_type: Literal["hotel", "home", "both"] | None = None

# Answer fields that are genuinely numeric. For these we extract a number even from
# free text with currency/units ("900 a persona", "750 €", "1.500 EUR"). Other fields
# (e.g. date_from "2026-08-16", destination text) must keep their string value, so we
# never run the aggressive numeric extraction on them.
_NUMERIC_FIELDS = {"budget_per_person", "trip_nights", "adults", "min_stars"}
# First number in free text, tolerating Italian thousands ('.') and decimal (',')
# separators and embedded spaces (e.g. "1.500", "1 500", "900,50").
_NUM_IN_TEXT = re.compile(r"\d[\d.\s]*(?:,\d+)?")


def _coerce_answer(value, field=None):
    """Coerce a free-text answer into a number when the field is numeric.

    Bare numbers always coerce ("900" -> 900). For numeric fields we also extract a
    number embedded in free text with currency/units or thousands separators, so a
    custom budget like "900 a persona" becomes 900 instead of being stored verbatim
    (which previously rendered as "NaN EUR" in the brief). Non-numeric fields and text
    without a number are returned unchanged."""
    if isinstance(value, (int, float)) or not isinstance(value, str):
        return value
    s = value.strip()
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except ValueError:
        pass
    if field in _NUMERIC_FIELDS:
        m = _NUM_IN_TEXT.search(s)
        if m:
            token = m.group(0).strip().replace(" ", "").replace(".", "").replace(",", ".")
            try:
                f = float(token)
                return int(f) if f.is_integer() else f
            except ValueError:
                pass
        # Numeric field, no number found (e.g. "quel che serve"): treat as "no constraint".
        return None
    return value


@router.post("/{chat_id}/messages")
async def post_message(chat_id: int, body: MessageIn,
                       db: AsyncSession = Depends(get_session),
                       user: User = Depends(get_current_user),
                       graph = Depends(get_graph)):
    perm = await user_chat_permission(db, chat_id, user)
    if perm is None:
        raise HTTPException(404, "Not found")
    if perm == "read":
        raise HTTPException(403, "Read-only")
    has_messages = (await db.execute(
        select(Message.id).where(Message.chat_id == chat_id).limit(1)
    )).first() is not None
    db.add(Message(chat_id=chat_id, role="user", content=body.content))
    await db.commit()
    rows = (await db.execute(select(Message).where(Message.chat_id == chat_id)
                             .order_by(Message.id))).scalars().all()
    history = [{"role": m.role, "content": m.content} for m in rows if m.role in ("user", "assistant")]
    state = {"chat_id": chat_id, "messages": history,
             "origin_coords": tuple(body.coords) if body.coords else None}
    if body.answer_to:
        state["prefill"] = {body.answer_to: _coerce_answer(body.content, body.answer_to)}
    # Search form controls are explicit request data, not prose for the LLM to infer. Put them
    # in prefill so intake deterministically wins over a stale/ambiguous extraction and the
    # values enter the checkpointed state on this turn.
    if body.search_mode is not None:
        state.setdefault("prefill", {})["search_mode"] = body.search_mode
    if body.accommodation_type is not None:
        state.setdefault("prefill", {})["accommodation_type"] = body.accommodation_type
    # The selection UI sends a "Genera altre opzioni" flag alongside the answer: the scout
    # uses it to keep the accumulated pool and propose a fresh batch instead of proceeding.
    if body.generate_more:
        prefill = state.setdefault("prefill", {})
        prefill["generate_more"] = True
    # Free-text typed alongside selected chips: guidance for the next batch of proposals.
    if body.refine_text and body.refine_text.strip():
        prefill = state.setdefault("prefill", {})
        prefill["refine_text"] = body.refine_text.strip()

    # Mark a run as in progress up front. A client that reloads mid-search reads this flag
    # and resumes (polls until it clears) instead of seeing an idle screen and assuming the
    # search was lost. For an answered question, also clear it now so a mid-run reload does
    # not re-ask it. Persisted independently of the (possibly still-running) graph.
    async with SessionLocal() as db0:
        chat0 = await db0.get(Chat, chat_id)
        if chat0 is not None:
            patch = {"run_active": True}
            if body.answer_to:
                patch["pending_question"] = None
            chat0.params_json = {**(chat0.params_json or {}), **patch}
        await db0.commit()

    queue: asyncio.Queue = asyncio.Queue()
    DONE = object()

    async def generate_persist_and_emit_title():
        title = await _title_from_first_message(body.content)
        async with SessionLocal() as db_title:
            chat = await db_title.get(Chat, chat_id)
            if chat is None:
                return
            current = (getattr(chat, "title", "") or "").strip()
            if current not in _AUTO_TITLE_PLACEHOLDERS:
                return
            chat.title = title
            await db_title.commit()
        await queue.put({"type": "chat_title", "chat_id": chat_id, "title": title})

    title_task = asyncio.create_task(generate_persist_and_emit_title()) if not has_messages else None

    # Capture request-scoped values now: the background task runs detached from the
    # request, so `user` and settings must be read before it is spawned.
    user_id = user.id
    model_name = get_settings().openai_model

    async def run_and_persist():
        """Drive the graph in a cancellable inner task and persist the outcome. The inner task
        is registered in _ACTIVE_RUNS so POST /{id}/stop can cancel it; this outer task is never
        cancelled, so its persistence in `finally` always runs cleanly."""
        acc = {"events": [], "final_message": "", "ranked": [], "brief": None, "question": None}
        tok = telemetry.start_run()
        t0 = time.monotonic()
        err = None
        stopped = False

        async def consume():
            async for ev in run_graph_events(graph, state, f"chat-{chat_id}"):
                acc["events"].append(ev)
                if ev["type"] == "message":
                    acc["final_message"] = ev["content"]
                elif ev["type"] == "package":
                    acc["ranked"].append(ev["data"])
                elif ev["type"] == "brief":
                    acc["brief"] = ev["data"]
                elif ev["type"] == "question":
                    acc["question"] = ev
                await queue.put(ev)

        # A second message on the same chat while a run is in flight would corrupt the shared
        # checkpoint (two writers on one thread_id) and orphan the older run in _ACTIVE_RUNS.
        # Last-writer-wins: cancel the previous run before starting this one.
        prev = _ACTIVE_RUNS.get(chat_id)
        if prev is not None and not prev.done():
            _SUPERSEDED.add(id(prev))
            prev.cancel()
        graph_task = asyncio.create_task(consume())
        _ACTIVE_RUNS[chat_id] = graph_task
        try:
            await asyncio.wait_for(graph_task, timeout=RUN_TIMEOUT_SECS)
        except asyncio.TimeoutError:
            err = "run_timeout"
            await queue.put({"type": "error",
                             "message": "La ricerca ha impiegato troppo tempo ed è stata "
                                        "interrotta. Riprova, magari con meno destinazioni."})
        except asyncio.CancelledError:
            stopped = True                       # POST /stop cancelled the inner task
        except Exception as exc:
            err = str(exc)
            await queue.put({"type": "error", "message": str(exc)})
        finally:
            # Deregister only our own task: a newer run for this chat may have replaced the
            # entry already, and popping blindly would make it un-stoppable.
            if _ACTIVE_RUNS.get(chat_id) is graph_task:
                _ACTIVE_RUNS.pop(chat_id, None)
            superseded = id(graph_task) in _SUPERSEDED
            _SUPERSEDED.discard(id(graph_task))
            events = acc["events"]
            brief, question = acc["brief"], acc["question"]
            final_message, ranked = acc["final_message"], acc["ranked"]
            if stopped and superseded:
                # Replaced by a newer message on the same chat: discard silently — no
                # "interrotta" bubble, and the chat's params/run_active belong to the new
                # run. Telemetry is still recorded below (tokens were really spent).
                final_message, ranked, question = "", [], None
                err = "superseded"
            elif stopped:
                # Hard cancel: discard agent output, keep only an "interrotto" note + the
                # partial step timeline. Tell any still-connected client to finalize.
                await queue.put({"type": "stopped"})
                final_message, ranked, question = STOPPED_MESSAGE, [], None
                err = "stopped_by_user"
            latency_ms = int((time.monotonic() - t0) * 1000)
            node_path: list[str] = []
            for ev in events:
                if ev.get("type") == "agent_step" and ev.get("status") == "running":
                    agent = ev.get("agent")
                    if agent and (not node_path or node_path[-1] != agent):
                        node_path.append(agent)
            usage = telemetry.snapshot()
            telemetry.reset(tok)
            async with SessionLocal() as db2:
                chat = await db2.get(Chat, chat_id)
                if chat is not None and not superseded:
                    params = {**(chat.params_json or {}), "run_active": False}
                    if brief is not None:
                        params = {**params, **brief, "pending_question": question}
                    elif stopped:
                        params = {**params, "pending_question": None}
                    chat.params_json = params
                msg_id = None
                if final_message or ranked:
                    m = Message(chat_id=chat_id, role="assistant", content=final_message,
                                tool_calls_json={"events": events, "ranked": ranked})
                    db2.add(m); await db2.flush(); msg_id = m.id
                try:
                    db2.add(RunTelemetry(
                        chat_id=chat_id, user_id=user_id, message_id=msg_id,
                        node_path=node_path,
                        prompt_tokens=usage["prompt_tokens"], completion_tokens=usage["completion_tokens"],
                        total_tokens=usage["total_tokens"], latency_ms=latency_ms,
                        model=model_name, ok=(err is None), error=err))
                except Exception:
                    pass
                await db2.commit()
            if title_task is not None:
                try:
                    await title_task
                except Exception:
                    pass
            await queue.put(DONE)

    task = asyncio.create_task(run_and_persist())
    _BACKGROUND_RUNS.add(task)
    task.add_done_callback(_BACKGROUND_RUNS.discard)

    async def gen():
        # The client connection only tails the queue; it never cancels the run. On a
        # client disconnect FastAPI closes this generator, but `run_and_persist`
        # continues and persists on its own.
        while True:
            try:
                ev = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECS)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
                continue
            if ev is DONE:
                break
            yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            if ev["type"] in ("error", "stopped"):
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                break

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/{chat_id}/stop")
async def stop_run(chat_id: int,
                   db: AsyncSession = Depends(get_session),
                   user: User = Depends(get_current_user)):
    perm = await user_chat_permission(db, chat_id, user)
    if perm is None:
        raise HTTPException(404, "Not found")
    if perm == "read":
        raise HTTPException(403, "Read-only")
    task = _ACTIVE_RUNS.get(chat_id)
    if task is not None and not task.done():
        task.cancel()
        return {"stopped": True}
    return {"stopped": False}
