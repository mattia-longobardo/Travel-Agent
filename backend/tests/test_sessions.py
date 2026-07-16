import fakeredis.aioredis
import pytest
from app.sessions import SessionStore


@pytest.mark.asyncio
async def test_session_lifecycle():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    store = SessionStore(r)
    sid = await store.create(42)
    assert await store.get(sid) == 42
    await store.delete(sid)
    assert await store.get(sid) is None


@pytest.mark.asyncio
async def test_delete_user_sessions():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    store = SessionStore(r)
    s1 = await store.create(7); s2 = await store.create(7)
    await store.delete_user_sessions(7)
    assert await store.get(s1) is None and await store.get(s2) is None
