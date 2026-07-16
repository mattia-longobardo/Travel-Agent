import fakeredis.aioredis
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.main import create_app
from app.models import Base, User, Group, RunTelemetry
from app.security import hash_password
from app.db import get_session
from app.sessions import SessionStore
from app.deps import get_session_store, get_graph


async def record_events(graph, state, thread_id):
    yield {"type": "agent_step", "agent": "intake", "status": "running", "label": "x"}
    yield {"type": "agent_step", "agent": "intake", "status": "done"}
    yield {"type": "agent_step", "agent": "scout", "status": "running", "label": "y"}
    yield {"type": "message", "content": "Ecco le proposte."}
    yield {"type": "done"}


@pytest.fixture
async def telemetry_client(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    redis = fakeredis.aioredis.FakeRedis()
    store = SessionStore(redis)
    async with sm() as s:
        g = Group(name="default"); s.add(g); await s.flush()
        s.add(User(username="bob", email="b@x", password_hash=hash_password("pw"), group_id=g.id))
        await s.commit()

    app = create_app()
    async def _get_session():
        async with sm() as s:
            yield s
    app.dependency_overrides[get_session] = _get_session
    app.dependency_overrides[get_session_store] = lambda: store
    app.dependency_overrides[get_graph] = lambda: object()
    monkeypatch.setattr("app.routers.agent.run_graph_events", record_events)
    monkeypatch.setattr("app.routers.agent.SessionLocal", lambda: sm())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://t") as c:
        c._sm = sm
        yield c


@pytest.mark.asyncio
async def test_one_telemetry_row_per_turn(telemetry_client):
    c = telemetry_client
    await c.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = (await c.post("/api/chats", json={"title": "x"})).json()["id"]
    resp = await c.post(f"/api/chats/{cid}/messages", json={"content": "Canarie agosto"})
    assert resp.status_code == 200
    async with c._sm() as db:
        rows = (await db.execute(select(RunTelemetry).where(RunTelemetry.chat_id == cid))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.node_path == ["intake", "scout"]
    assert row.ok is True
    assert row.message_id is not None
