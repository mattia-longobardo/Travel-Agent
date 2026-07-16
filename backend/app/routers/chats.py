from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.deps import get_current_user
from app.chat_access import user_chat_permission
from app.models import Chat, ChatGroup, ChatShare, Message, RunTelemetry, User
from app.schemas import ChatCreate, ChatOut, ChatUpdate, ShareIn, MessageOut

router = APIRouter(prefix="/api/chats", tags=["chats"])


def _chat_out(c, permission):
    return ChatOut(id=c.id, title=c.title, params_json=c.params_json, owner_id=c.owner_id,
                   permission=permission, status=c.status, chat_group_id=c.chat_group_id)


@router.get("", response_model=list[ChatOut])
async def list_chats(status: str | None = None,
                     db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    owned_q = select(Chat).where(Chat.owner_id == user.id)
    owned_q = owned_q.where(Chat.status == status) if status else owned_q.where(Chat.status != "trashed")
    owned = (await db.execute(owned_q)).scalars().all()
    shared_ids = (await db.execute(
        select(ChatShare.chat_id).where(ChatShare.user_id == user.id))).scalars().all()
    shared = (await db.execute(select(Chat).where(Chat.id.in_(shared_ids)))).scalars().all() if shared_ids else []
    out = [_chat_out(c, "owner") for c in owned]
    out += [_chat_out(c, "shared") for c in shared]
    return out


@router.post("", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
async def create_chat(body: ChatCreate, db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    c = Chat(owner_id=user.id, title=body.title or "Nuova chat", params_json=body.params)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return _chat_out(c, "owner")


@router.post("/empty-trash")
async def empty_trash(db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    ids = (await db.execute(
        select(Chat.id).where(Chat.owner_id == user.id, Chat.status == "trashed"))).scalars().all()
    if ids:
        # run_telemetry FKs chats.id AND messages.id, so it must be cleared first or Postgres
        # rejects the message/chat deletes with a ForeignKeyViolation.
        await db.execute(delete(RunTelemetry).where(RunTelemetry.chat_id.in_(ids)))
        await db.execute(delete(Message).where(Message.chat_id.in_(ids)))
        await db.execute(delete(ChatShare).where(ChatShare.chat_id.in_(ids)))
        await db.execute(delete(Chat).where(Chat.id.in_(ids)))
        await db.commit()
    return {"status": "ok", "deleted": len(ids)}


async def _require_access(db, chat_id, user, need_write=False):
    perm = await user_chat_permission(db, chat_id, user)
    if perm is None:
        raise HTTPException(404, "Not found")
    if need_write and perm == "read":
        raise HTTPException(403, "Read-only")
    return perm


@router.get("/{chat_id}", response_model=ChatOut)
async def get_chat(chat_id: int, db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    perm = await _require_access(db, chat_id, user)
    c = await db.get(Chat, chat_id)
    return _chat_out(c, perm)


@router.patch("/{chat_id}", response_model=ChatOut)
async def update_chat(chat_id: int, body: ChatUpdate, db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    perm = await _require_access(db, chat_id, user, need_write=True)
    c = await db.get(Chat, chat_id)
    if body.title is not None:
        c.title = body.title
    if body.params is not None:
        c.params_json = body.params
    if body.status is not None:
        if body.status not in ("active", "archived", "trashed"):
            raise HTTPException(422, "Bad status")
        c.status = body.status
        c.trashed_at = datetime.now(timezone.utc) if body.status == "trashed" else None
    if "chat_group_id" in body.model_fields_set:
        gid = body.chat_group_id or None
        if gid is not None:
            grp = await db.get(ChatGroup, gid)
            if grp is None or grp.owner_id != user.id:
                raise HTTPException(404, "Group not found")
        c.chat_group_id = gid
    await db.commit()
    await db.refresh(c)
    return _chat_out(c, perm)


@router.delete("/{chat_id}")
async def delete_chat(chat_id: int, db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    perm = await _require_access(db, chat_id, user)
    if perm != "owner":
        raise HTTPException(403, "Owner only")
    # run_telemetry FKs chats.id AND messages.id, so it must be cleared first or Postgres
    # rejects the message/chat deletes with a ForeignKeyViolation.
    await db.execute(delete(RunTelemetry).where(RunTelemetry.chat_id == chat_id))
    await db.execute(delete(Message).where(Message.chat_id == chat_id))
    await db.execute(delete(ChatShare).where(ChatShare.chat_id == chat_id))
    await db.execute(delete(Chat).where(Chat.id == chat_id))
    await db.commit()
    return {"status": "ok"}


@router.get("/{chat_id}/messages", response_model=list[MessageOut])
async def list_messages(chat_id: int, db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    await _require_access(db, chat_id, user)
    rows = (await db.execute(select(Message).where(Message.chat_id == chat_id).order_by(Message.id))).scalars().all()
    return rows


@router.post("/{chat_id}/share")
async def share_chat(chat_id: int, body: ShareIn, db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    perm = await _require_access(db, chat_id, user)
    if perm != "owner":
        raise HTTPException(403, "Owner only")
    target = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if not target:
        raise HTTPException(404, "User not found")
    if body.permission not in ("read", "write"):
        raise HTTPException(422, "Bad permission")
    existing = await db.get(ChatShare, {"chat_id": chat_id, "user_id": target.id})
    if existing:
        existing.permission = body.permission
    else:
        db.add(ChatShare(chat_id=chat_id, user_id=target.id, permission=body.permission))
    await db.commit()
    return {"status": "ok"}


@router.delete("/{chat_id}/share/{user_id}")
async def unshare_chat(chat_id: int, user_id: int, db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    perm = await _require_access(db, chat_id, user)
    if perm != "owner":
        raise HTTPException(403, "Owner only")
    await db.execute(delete(ChatShare).where(ChatShare.chat_id == chat_id, ChatShare.user_id == user_id))
    await db.commit()
    return {"status": "ok"}
