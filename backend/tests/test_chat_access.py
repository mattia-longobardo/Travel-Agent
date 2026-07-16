import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.models import Base, User, Chat, ChatShare
from app.chat_access import user_chat_permission

@pytest.mark.asyncio
async def test_permissions():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as s:
        owner = User(username="o", email="o", password_hash="h"); s.add(owner)
        other = User(username="x", email="x", password_hash="h"); s.add(other)
        await s.flush()
        chat = Chat(owner_id=owner.id, title="t"); s.add(chat); await s.flush()
        s.add(ChatShare(chat_id=chat.id, user_id=other.id, permission="read"))
        await s.commit()
        assert await user_chat_permission(s, chat.id, owner) == "owner"
        assert await user_chat_permission(s, chat.id, other) == "read"
        stranger = User(username="z", email="z", password_hash="h"); s.add(stranger); await s.flush()
        assert await user_chat_permission(s, chat.id, stranger) is None
