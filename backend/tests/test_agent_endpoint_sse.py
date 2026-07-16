import asyncio
import pytest
from app.deps import get_graph

class _FakeDB:
    def add(self, *a, **k): pass
    async def get(self, *a): return None
    async def flush(self): pass
    async def commit(self): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False


class _FakeChat:
    def __init__(self, title="Nuova chat"):
        self.params_json = {}
        self.title = title


class _CapturingDB:
    """Records mutations to a shared chat object so a test can inspect params_json."""
    def __init__(self, chat): self.chat = chat; self.added = []
    def add(self, obj): self.added.append(obj)
    async def get(self, model, pk): return self.chat
    async def flush(self): pass
    async def commit(self): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False

async def fake_events(graph, state, thread_id):
    yield {"type": "agent_step", "agent": "intake", "status": "running", "label": "x"}
    yield {"type": "package", "data": {"id": "pkg-1", "destination": "Tenerife (TFS)",
           "price_per_person": 350, "currency": "EUR"}}
    yield {"type": "message", "content": "Ecco le proposte."}
    yield {"type": "done"}


async def done_events(graph, state, thread_id):
    yield {"type": "done"}

@pytest.mark.asyncio
async def test_post_message_streams_events(app_client, monkeypatch):
    app = app_client._transport.app
    app.dependency_overrides[get_graph] = lambda: object()  # dummy; run_graph_events is patched
    monkeypatch.setattr("app.routers.agent.run_graph_events", fake_events)
    monkeypatch.setattr("app.routers.agent.SessionLocal", lambda: _FakeDB())
    await app_client.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = (await app_client.post("/api/chats", json={"title": "x"})).json()["id"]
    resp = await app_client.post(f"/api/chats/{cid}/messages",
                                 json={"content": "Canarie agosto", "coords": [45.46, 9.19]})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "agent_step" in body and "pkg-1" in body and '"type": "done"' in body


@pytest.mark.asyncio
async def test_post_message_puts_explicit_search_controls_in_prefill(app_client, monkeypatch):
    captured = {}

    async def capture_events(graph, state, thread_id):
        captured.update(state)
        yield {"type": "done"}

    app = app_client._transport.app
    app.dependency_overrides[get_graph] = lambda: object()
    monkeypatch.setattr("app.routers.agent.run_graph_events", capture_events)
    monkeypatch.setattr("app.routers.agent.SessionLocal", lambda: _FakeDB())
    await app_client.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = (await app_client.post("/api/chats", json={"title": "x"})).json()["id"]
    resp = await app_client.post(f"/api/chats/{cid}/messages", json={
        "content": "Roma", "search_mode": "hotel_only", "accommodation_type": "home",
    })
    assert resp.status_code == 200
    assert captured["prefill"] == {"search_mode": "hotel_only", "accommodation_type": "home"}


@pytest.mark.asyncio
async def test_first_message_emits_generated_chat_title(app_client, monkeypatch):
    chat = _FakeChat()
    app = app_client._transport.app
    app.dependency_overrides[get_graph] = lambda: object()

    async def title(_first_message):
        return "Canarie ad agosto"

    monkeypatch.setattr("app.routers.agent.run_graph_events", done_events)
    monkeypatch.setattr("app.routers.agent._title_from_first_message", title)
    monkeypatch.setattr("app.routers.agent.SessionLocal", lambda: _CapturingDB(chat))
    await app_client.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = (await app_client.post("/api/chats", json={})).json()["id"]
    resp = await app_client.post(f"/api/chats/{cid}/messages", json={"content": "Canarie agosto"})

    assert resp.status_code == 200
    assert '"type": "chat_title"' in resp.text
    assert '"title": "Canarie ad agosto"' in resp.text
    assert chat.title == "Canarie ad agosto"


async def slow_events(graph, state, thread_id):
    await asyncio.sleep(0.06)
    yield {"type": "message", "content": "ok"}
    yield {"type": "done"}


@pytest.mark.asyncio
async def test_sse_emits_heartbeat_during_silent_gaps(app_client, monkeypatch):
    app = app_client._transport.app
    app.dependency_overrides[get_graph] = lambda: object()
    monkeypatch.setattr("app.routers.agent.HEARTBEAT_SECS", 0.01)
    monkeypatch.setattr("app.routers.agent.run_graph_events", slow_events)
    monkeypatch.setattr("app.routers.agent.SessionLocal", lambda: _FakeDB())
    await app_client.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = (await app_client.post("/api/chats", json={"title": "x"})).json()["id"]
    resp = await app_client.post(f"/api/chats/{cid}/messages", json={"content": "x"})
    body = resp.text
    assert "keep-alive" in body, "heartbeat must be emitted during the silent gap"
    assert '"type": "done"' in body


_QUESTION = {"type": "question", "id": "budget_per_person", "text": "Budget?",
             "options": [{"label": "≤ 500 €", "value": 500}], "allow_free_text": True}


async def question_events(graph, state, thread_id):
    yield {"type": "brief", "data": {"date_from": "2026-08-18", "adults": 2}}
    yield _QUESTION
    yield {"type": "done"}


async def answer_events(graph, state, thread_id):
    yield {"type": "brief", "data": {"date_from": "2026-08-18", "adults": 2}}
    yield {"type": "package", "data": {"id": "pkg-1", "destination": "Tenerife (TFS)"}}
    yield {"type": "message", "content": "Ecco le proposte."}
    yield {"type": "done"}


@pytest.mark.asyncio
async def test_question_turn_persists_pending_question(app_client, monkeypatch):
    chat = _FakeChat()
    app = app_client._transport.app
    app.dependency_overrides[get_graph] = lambda: object()
    monkeypatch.setattr("app.routers.agent.run_graph_events", question_events)
    monkeypatch.setattr("app.routers.agent.SessionLocal", lambda: _CapturingDB(chat))
    await app_client.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = (await app_client.post("/api/chats", json={"title": "x"})).json()["id"]
    await app_client.post(f"/api/chats/{cid}/messages", json={"content": "Canarie"})
    assert chat.params_json.get("pending_question") == _QUESTION
    # brief is still merged alongside it
    assert chat.params_json.get("adults") == 2


@pytest.mark.asyncio
async def test_answer_turn_clears_pending_question(app_client, monkeypatch):
    chat = _FakeChat()
    chat.params_json = {"pending_question": _QUESTION, "adults": 2}
    app = app_client._transport.app
    app.dependency_overrides[get_graph] = lambda: object()
    monkeypatch.setattr("app.routers.agent.run_graph_events", answer_events)
    monkeypatch.setattr("app.routers.agent.SessionLocal", lambda: _CapturingDB(chat))
    await app_client.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = (await app_client.post("/api/chats", json={"title": "x"})).json()["id"]
    await app_client.post(f"/api/chats/{cid}/messages", json={"content": "750"})
    assert chat.params_json.get("pending_question") is None


async def brief_message_events(graph, state, thread_id):
    """A run that yields a brief, a message and done — used to prove persistence
    survives even when the client disconnects after the first event."""
    yield {"type": "brief", "data": {"date_from": "2026-08-18", "adults": 2}}
    yield {"type": "package", "data": {"id": "pkg-1", "destination": "Tenerife (TFS)"}}
    yield {"type": "message", "content": "Ecco le proposte."}
    yield {"type": "done"}


@pytest.mark.asyncio
async def test_run_persists_even_if_client_disconnects_early(app_client, monkeypatch):
    """The user navigates away mid-run: we consume only the first SSE event then
    drop the connection. The detached run must still complete and persist."""
    chat = _FakeChat()
    app = app_client._transport.app
    app.dependency_overrides[get_graph] = lambda: object()
    monkeypatch.setattr("app.routers.agent.run_graph_events", brief_message_events)
    monkeypatch.setattr("app.routers.agent.SessionLocal", lambda: _CapturingDB(chat))
    await app_client.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = (await app_client.post("/api/chats", json={"title": "x"})).json()["id"]

    async with app_client.stream(
        "POST", f"/api/chats/{cid}/messages", json={"content": "Canarie"}
    ) as resp:
        async for _line in resp.aiter_lines():
            break  # consume only the first chunk, then disconnect

    # The detached run keeps going and persists on its own; give the loop a beat.
    for _ in range(50):
        if chat.params_json.get("adults") == 2:
            break
        await asyncio.sleep(0.01)
    assert chat.params_json.get("adults") == 2  # brief persisted
    assert chat.params_json.get("pending_question") is None  # resolved turn


@pytest.mark.asyncio
async def test_answer_to_clears_pending_question_up_front(app_client, monkeypatch):
    """When body.answer_to is set, the previously-stored pending_question is cleared
    immediately (before/independent of the run finishing), so a mid-run return does
    not re-ask it. We use a run that never yields a brief to prove the up-front clear
    is what zeroed it."""
    chat = _FakeChat()
    chat.params_json = {"pending_question": _QUESTION, "adults": 2}
    app = app_client._transport.app
    app.dependency_overrides[get_graph] = lambda: object()

    async def silent_run(graph, state, thread_id):
        yield {"type": "done"}

    monkeypatch.setattr("app.routers.agent.run_graph_events", silent_run)
    monkeypatch.setattr("app.routers.agent.SessionLocal", lambda: _CapturingDB(chat))
    await app_client.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = (await app_client.post("/api/chats", json={"title": "x"})).json()["id"]
    await app_client.post(
        f"/api/chats/{cid}/messages",
        json={"content": "750", "answer_to": "budget_per_person"},
    )
    assert chat.params_json.get("pending_question") is None
    assert chat.params_json.get("adults") == 2  # other params untouched


@pytest.mark.asyncio
async def test_run_active_marker_set_up_front_and_cleared_at_end(app_client, monkeypatch):
    """A run marks `run_active` True before it starts (so a reloaded client can detect a
    search in progress and resume it) and clears it to False when it finishes — even when
    the turn yields no brief/message."""
    chat = _FakeChat()
    seen = {}

    async def run(graph, state, thread_id):
        # By the time the detached run executes, the up-front commit has happened.
        seen["active_during"] = chat.params_json.get("run_active")
        yield {"type": "message", "content": "ok"}
        yield {"type": "done"}

    app = app_client._transport.app
    app.dependency_overrides[get_graph] = lambda: object()
    monkeypatch.setattr("app.routers.agent.run_graph_events", run)
    monkeypatch.setattr("app.routers.agent.SessionLocal", lambda: _CapturingDB(chat))
    await app_client.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = (await app_client.post("/api/chats", json={"title": "x"})).json()["id"]
    await app_client.post(f"/api/chats/{cid}/messages", json={"content": "Canarie"})

    for _ in range(50):
        if chat.params_json.get("run_active") is False:
            break
        await asyncio.sleep(0.01)
    assert seen["active_during"] is True            # set before the run started
    assert chat.params_json.get("run_active") is False  # cleared in the run's finally


async def stop_slow_events(graph, state, thread_id):
    # First event registers + flushes the run; then a long wait we will cancel.
    yield {"type": "agent_step", "agent": "intake", "status": "running", "label": "x"}
    await asyncio.sleep(5)
    yield {"type": "message", "content": "MAI"}
    yield {"type": "done"}


@pytest.mark.asyncio
async def test_stop_cancels_in_flight_run(app_client, monkeypatch):
    chat = _FakeChat()
    added = []
    # httpx.ASGITransport.handle_async_request runs `await app(scope, receive, send)` to
    # completion before returning, so the full SSE body is buffered before the client sees
    # any of it. An inline `async with client.stream(...)` can therefore never interleave
    # with a concurrent /stop request. Workaround: run the SSE request in a background
    # task and use an asyncio.Event to know when _ACTIVE_RUNS is populated.
    run_in_flight = asyncio.Event()

    class CapDB:
        def add(self, obj): added.append(obj)
        async def get(self, model, pk): return chat
        async def flush(self): pass
        async def commit(self): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False

    app = app_client._transport.app
    app.dependency_overrides[get_graph] = lambda: object()

    async def events_with_signal(graph, state, thread_id):
        """Wraps stop_slow_events; signals once the first event is in-flight (and
        therefore _ACTIVE_RUNS[chat_id] is already set by run_and_persist)."""
        async for ev in stop_slow_events(graph, state, thread_id):
            if not run_in_flight.is_set():
                run_in_flight.set()
            yield ev

    monkeypatch.setattr("app.routers.agent.run_graph_events", events_with_signal)
    monkeypatch.setattr("app.routers.agent.SessionLocal", lambda: CapDB())
    await app_client.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = (await app_client.post("/api/chats", json={"title": "x"})).json()["id"]

    stream_task = asyncio.create_task(
        app_client.post(f"/api/chats/{cid}/messages", json={"content": "Canarie"})
    )
    # Yield to the event loop until the first event is processed and the run is registered.
    await run_in_flight.wait()
    stop = await app_client.post(f"/api/chats/{cid}/stop")
    assert stop.json() == {"stopped": True}
    resp = await stream_task
    rest = resp.text

    assert '"type": "stopped"' in rest            # stopped event reached the client (exact JSON)
    for _ in range(100):
        if chat.params_json.get("run_active") is False:
            break
        await asyncio.sleep(0.01)
    assert chat.params_json.get("run_active") is False
    msgs = [o for o in added if getattr(o, "role", None) == "assistant"]
    assert msgs and msgs[0].tool_calls_json["ranked"] == []      # proposals discarded
    assert msgs[0].tool_calls_json["events"]                     # partial timeline kept
    assert "interrotta" in (msgs[0].content or "").lower()
    tels = [o for o in added if o.__class__.__name__ == "RunTelemetry"]
    assert tels and tels[0].error == "stopped_by_user"


@pytest.mark.asyncio
async def test_stop_no_active_run_returns_false(app_client):
    await app_client.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = (await app_client.post("/api/chats", json={"title": "x"})).json()["id"]
    resp = await app_client.post(f"/api/chats/{cid}/stop")
    assert resp.status_code == 200
    assert resp.json() == {"stopped": False}


@pytest.mark.asyncio
async def test_stop_unknown_chat_returns_404(app_client):
    await app_client.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    resp = await app_client.post("/api/chats/999999/stop")
    assert resp.status_code == 404
