from functools import lru_cache
from fastapi import Cookie, Depends, HTTPException
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.models import User
from app.sessions import SessionStore
from app.redis_client import get_redis
from app.config import get_settings
from app.agent.mcp_manager import McpManager

COOKIE_NAME = "travel_session"

def get_session_store() -> SessionStore:
    return SessionStore(get_redis())

async def get_current_user(
    travel_session: str | None = Cookie(default=None),
    store: SessionStore = Depends(get_session_store),
    db: AsyncSession = Depends(get_session),
) -> User:
    if not travel_session:
        raise HTTPException(401, "Not authenticated")
    user_id = await store.get(travel_session)
    if user_id is None:
        raise HTTPException(401, "Invalid session")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "Invalid session")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")
    return user

async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Admin only")
    return user


@lru_cache
def get_openai() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


@lru_cache
def get_mcp() -> McpManager:
    settings = get_settings()
    servers = {}
    if settings.lastminute_mcp_url:
        servers["lastminute"] = {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "mcp-remote", settings.lastminute_mcp_url],
        }
    return McpManager(servers)


from app.agent.llm import OpenAILLM
from app.agent.graph import build_graph


@lru_cache
def get_graph():
    settings = get_settings()
    llm = OpenAILLM(get_openai(), settings.openai_model)
    mcp = get_mcp()
    try:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
    except Exception:
        checkpointer = None
    return build_graph(llm, mcp, web_search=None, checkpointer=checkpointer)
