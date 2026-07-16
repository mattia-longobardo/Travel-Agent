import fakeredis.aioredis
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.main import create_app
from app.models import Base, User, Group
from app.security import hash_password
from app.db import get_session
from app.sessions import SessionStore
from app.deps import get_session_store

@pytest.fixture
async def app_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    redis = fakeredis.aioredis.FakeRedis()
    store = SessionStore(redis)

    async with sm() as s:
        g = Group(name="default"); s.add(g); await s.flush()
        s.add(User(username="admin", email="a@x", password_hash=hash_password("pw"),
                   group_id=g.id, is_admin=True))
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
        yield c
