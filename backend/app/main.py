import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routers import auth, admin, chats, agent, chat_groups, me, go, properties
from app.db import SessionLocal
from app.config import get_settings
from app.bootstrap import clear_stale_run_flags, ensure_admin
from app.pricing import refresh_pricing

log = logging.getLogger(__name__)


async def _pricing_refresher():
    # refresh_pricing no-ops while the cache is fresh, so an hourly tick just
    # retries failed fetches and picks up the daily refresh.
    while True:
        try:
            await asyncio.to_thread(refresh_pricing)
        except Exception:
            log.exception("pricing refresh crashed")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SessionLocal() as db:
        await ensure_admin(db, get_settings())
        await clear_stale_run_flags(db)
    pricing_task = asyncio.create_task(_pricing_refresher())
    try:
        yield
    finally:
        pricing_task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="Travel Agent API", lifespan=lifespan,
                  docs_url="/api/docs", openapi_url="/api/openapi.json")

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(chats.router)
    app.include_router(chat_groups.router)
    app.include_router(me.router)
    app.include_router(agent.router)
    app.include_router(go.router)
    app.include_router(properties.router)
    return app

app = create_app()
