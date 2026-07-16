from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.deps import get_current_user
from app.models import Chat, ChatGroup, User
from app.schemas import ChatGroupIn

router = APIRouter(prefix="/api/chat-groups", tags=["chat-groups"])


async def _own_group(db, gid, user) -> ChatGroup:
    g = await db.get(ChatGroup, gid)
    if g is None or g.owner_id != user.id:
        raise HTTPException(404, "Not found")
    return g


@router.get("")
async def list_groups(db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    rows = (await db.execute(
        select(ChatGroup).where(ChatGroup.owner_id == user.id).order_by(ChatGroup.id))).scalars().all()
    return [{"id": g.id, "name": g.name} for g in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_group(body: ChatGroupIn, db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    g = ChatGroup(owner_id=user.id, name=body.name or "Gruppo")
    db.add(g); await db.commit(); await db.refresh(g)
    return {"id": g.id, "name": g.name}


@router.patch("/{gid}")
async def rename_group(gid: int, body: ChatGroupIn, db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    g = await _own_group(db, gid, user)
    g.name = body.name
    await db.commit()
    return {"id": g.id, "name": g.name}


@router.delete("/{gid}")
async def delete_group(gid: int, db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    g = await _own_group(db, gid, user)
    await db.execute(update(Chat).where(Chat.chat_group_id == gid).values(
        chat_group_id=None, status="trashed", trashed_at=datetime.now(timezone.utc)))
    await db.delete(g)
    await db.commit()
    return {"status": "ok"}
