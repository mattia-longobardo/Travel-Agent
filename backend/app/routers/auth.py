from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.deps import COOKIE_NAME, get_current_user, get_session_store
from app.models import User
from app.schemas import LoginIn, UserOut
from app.security import normalize_email, verify_password
from app.sessions import SessionStore

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login", response_model=UserOut)
async def login(body: LoginIn, response: Response,
                db: AsyncSession = Depends(get_session),
                store: SessionStore = Depends(get_session_store)):
    user = (await db.execute(select(User).where(User.email == normalize_email(body.email)))).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")
    sid = await store.create(user.id)
    response.set_cookie(COOKIE_NAME, sid, httponly=True, secure=True, samesite="lax", max_age=7*24*3600, path="/")
    return user

@router.post("/logout")
async def logout(response: Response,
                 travel_session: str | None = Cookie(default=None),
                 store: SessionStore = Depends(get_session_store)):
    if travel_session:
        await store.delete(travel_session)
    response.delete_cookie(COOKIE_NAME, path="/", secure=True, samesite="lax")
    return {"status": "ok"}

@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
