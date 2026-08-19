import redis.asyncio as redis
from app.config import get_settings

_settings = get_settings()
_pool = redis.ConnectionPool(
    host=_settings.redis_host,
    port=_settings.redis_port,
    password=_settings.redis_password or None,
    db=_settings.redis_db,
    decode_responses=True,
)

def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=_pool)
