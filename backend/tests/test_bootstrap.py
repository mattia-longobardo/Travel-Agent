import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.models import Base, User
from app.bootstrap import ensure_admin
from app.config import Settings
from sqlalchemy import select

@pytest.mark.asyncio
async def test_ensure_admin_idempotent():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    st = Settings(admin_username="root", admin_password="pw", admin_email="r@x")
    async with sm() as s:
        await ensure_admin(s, st)
        await ensure_admin(s, st)  # second call must not duplicate
        admins = (await s.execute(select(User).where(User.is_admin == True))).scalars().all()
    assert len(admins) == 1 and admins[0].username == "root"


@pytest.mark.asyncio
async def test_clear_stale_run_flags():
    """A crash/redeploy mid-run leaves run_active=True with no task behind it; startup must
    clear it (or clients poll a spinner forever), preserving the rest of params_json."""
    from app.bootstrap import clear_stale_run_flags
    from app.models import Chat, Group
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    st = Settings(admin_username="root", admin_password="pw", admin_email="r@x")
    async with sm() as s:
        await ensure_admin(s, st)
        admin = (await s.execute(select(User))).scalars().first()
        s.add(Chat(owner_id=admin.id, title="a",
                   params_json={"run_active": True, "adults": 2}))
        s.add(Chat(owner_id=admin.id, title="b", params_json={"adults": 1}))
        s.add(Chat(owner_id=admin.id, title="c", params_json=None))
        await s.commit()
    async with sm() as s:
        assert await clear_stale_run_flags(s) == 1
        chats = (await s.execute(select(Chat).order_by(Chat.id))).scalars().all()
        assert chats[0].params_json == {"run_active": False, "adults": 2}
        assert chats[1].params_json == {"adults": 1}
    async with sm() as s:
        assert await clear_stale_run_flags(s) == 0  # idempotent
