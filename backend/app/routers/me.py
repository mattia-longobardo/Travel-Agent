from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas import MeUpdate, UserOut
from app.security import hash_password, normalize_email, verify_password

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("", response_model=UserOut)
async def update_me(body: MeUpdate, db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    if body.username is not None and body.username != user.username:
        dup = (await db.execute(select(User).where(User.username == body.username))).scalar_one_or_none()
        if dup:
            raise HTTPException(409, "Username già in uso")
        user.username = body.username
    if body.email is not None:
        email = normalize_email(body.email)
        if email != user.email:
            dup = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if dup:
                raise HTTPException(409, "Email già in uso")
            user.email = email
    if body.new_password:
        if not body.current_password or not verify_password(body.current_password, user.password_hash):
            raise HTTPException(400, "Password attuale errata")
        user.password_hash = hash_password(body.new_password)
    await db.commit()
    await db.refresh(user)
    return user
