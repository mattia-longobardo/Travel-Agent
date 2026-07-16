import secrets

SESSION_TTL = 7 * 24 * 3600


class SessionStore:
    def __init__(self, redis):
        self.r = redis

    async def create(self, user_id: int) -> str:
        sid = secrets.token_urlsafe(32)
        await self.r.set(f"sess:{sid}", user_id, ex=SESSION_TTL)
        await self.r.sadd(f"usess:{user_id}", sid)
        await self.r.expire(f"usess:{user_id}", SESSION_TTL)
        return sid

    async def get(self, sid: str) -> int | None:
        val = await self.r.get(f"sess:{sid}")
        return int(val) if val is not None else None

    async def delete(self, sid: str) -> None:
        # Get user_id to clean up from user sessions set
        user_id = await self.get(sid)
        await self.r.delete(f"sess:{sid}")
        if user_id is not None:
            await self.r.srem(f"usess:{user_id}", sid)

    async def delete_user_sessions(self, user_id: int) -> None:
        sids = await self.r.smembers(f"usess:{user_id}")
        for sid in sids:
            await self.r.delete(f"sess:{sid}")
        await self.r.delete(f"usess:{user_id}")
