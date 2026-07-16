from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Chat, ChatShare, User

async def user_chat_permission(db: AsyncSession, chat_id: int, user: User) -> str | None:
    chat = await db.get(Chat, chat_id)
    if chat is None:
        return None
    if chat.owner_id == user.id:
        return "owner"
    share = (await db.execute(
        select(ChatShare).where(ChatShare.chat_id == chat_id, ChatShare.user_id == user.id)
    )).scalar_one_or_none()
    return share.permission if share else None
