"""Regression: deleting a chat (or emptying the trash) must also purge the chat's
``run_telemetry`` rows.

``RunTelemetry`` carries FKs to ``chats.id`` and ``messages.id`` (added with the analytics
feature). Production runs on Postgres, which enforces those FKs, so deleting messages/chats
without first removing the telemetry rows raises a ForeignKeyViolation -> 500 ("Elimina
definitivamente" / "Svuota cestino" silently fail). The shared test suite uses SQLite with FK
enforcement OFF, which hid the bug; this fixture turns FK enforcement ON to reproduce prod.
"""
import fakeredis.aioredis
import httpx
import pytest
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import get_session
from app.deps import get_session_store
from app.main import create_app
from app.models import Base, Chat, Group, Message, RunTelemetry, User
from app.security import hash_password
from app.sessions import SessionStore


@pytest.fixture
async def fk_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # Reproduce Postgres' referential integrity: SQLite ignores FKs unless asked.
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_fk(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

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
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://t") as c:
        c._sm = sm
        yield c


async def _seed_chat_with_telemetry(sm, owner_email="b@x"):
    """Create a chat owned by *owner_email* with one message and one telemetry row."""
    async with sm() as s:
        owner = (await s.execute(select(User).where(User.email == owner_email))).scalar_one()
        chat = Chat(owner_id=owner.id, title="x", status="active")
        s.add(chat); await s.flush()
        msg = Message(chat_id=chat.id, role="user", content="hi")
        s.add(msg); await s.flush()
        s.add(RunTelemetry(chat_id=chat.id, user_id=owner.id, message_id=msg.id))
        await s.commit()
        return chat.id


async def _telemetry_count(sm, chat_id):
    async with sm() as s:
        return len((await s.execute(
            select(RunTelemetry).where(RunTelemetry.chat_id == chat_id))).scalars().all())


@pytest.mark.asyncio
async def test_delete_chat_purges_telemetry(fk_client):
    c = fk_client
    await c.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = await _seed_chat_with_telemetry(c._sm)
    assert await _telemetry_count(c._sm, cid) == 1

    r = await c.request("DELETE", f"/api/chats/{cid}")
    assert r.status_code == 200, r.text
    assert await _telemetry_count(c._sm, cid) == 0
    assert (await c.get(f"/api/chats/{cid}")).status_code == 404


@pytest.mark.asyncio
async def test_empty_trash_purges_telemetry(fk_client):
    c = fk_client
    await c.post("/api/auth/login", json={"email": "b@x", "password": "pw"})
    cid = await _seed_chat_with_telemetry(c._sm)
    await c.patch(f"/api/chats/{cid}", json={"status": "trashed"})

    r = await c.post("/api/chats/empty-trash")
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] == 1
    assert await _telemetry_count(c._sm, cid) == 0
    assert (await c.get("/api/chats?status=trashed")).json() == []
