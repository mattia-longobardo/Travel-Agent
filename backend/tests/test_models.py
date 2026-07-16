import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.models import Base, User, Group, RunTelemetry


def test_run_telemetry_schema():
    assert RunTelemetry.__tablename__ == "run_telemetry"
    cols = set(RunTelemetry.__table__.columns.keys())
    for c in ("chat_id", "user_id", "node_path", "total_tokens", "latency_ms", "ok", "created_at"):
        assert c in cols

@pytest.mark.asyncio
async def test_user_roundtrip():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as s:
        g = Group(name="default")
        s.add(g); await s.flush()
        u = User(username="a", email="a@x", password_hash="h", group_id=g.id)
        s.add(u); await s.commit()
        assert u.id is not None
        assert u.is_active is True and u.is_admin is False
