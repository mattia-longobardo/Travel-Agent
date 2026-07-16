from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Chat, Group, User
from app.security import hash_password, normalize_email


async def clear_stale_run_flags(db: AsyncSession) -> int:
    """Clear ``run_active`` markers orphaned by a crash/redeploy mid-run.

    The flag is set before a run and cleared when it persists its outcome; the runs
    themselves live only in this process, so after a restart any chat still marked
    ``run_active`` has no task behind it and the client would poll a spinner forever.
    Returns the number of chats cleaned."""
    rows = (await db.execute(select(Chat))).scalars().all()
    cleaned = 0
    for chat in rows:
        params = chat.params_json or {}
        if params.get("run_active"):
            chat.params_json = {**params, "run_active": False}
            cleaned += 1
    if cleaned:
        await db.commit()
    return cleaned


async def ensure_admin(db: AsyncSession, settings) -> None:
    existing = (await db.execute(select(User).where(User.is_admin == True))).scalar_one_or_none()
    if existing:
        return
    group = (await db.execute(select(Group).where(Group.name == "default"))).scalar_one_or_none()
    if not group:
        group = Group(name="default"); db.add(group); await db.flush()
    db.add(User(username=settings.admin_username, email=normalize_email(settings.admin_email),
                password_hash=hash_password(settings.admin_password),
                group_id=group.id, is_admin=True, is_active=True))
    await db.commit()
