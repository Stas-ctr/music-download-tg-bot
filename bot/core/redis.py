import hashlib
import time
from typing import Optional

import redis.asyncio as aioredis

from core.config import settings

redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> aioredis.Redis:
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=10,
    )
    await redis_client.ping()
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


def _cache_key(query: str) -> str:
    h = hashlib.md5(query.lower().strip().encode()).hexdigest()
    return f"cache:{h}"


async def set_search_session(short_id: str, tracks: list[dict]):
    if not redis_client:
        return
    import json
    await redis_client.setex(
        f"srch:{short_id}",
        settings.CACHE_TTL,
        json.dumps(tracks, ensure_ascii=False),
    )


async def get_search_session(short_id: str) -> Optional[list[dict]]:
    if not redis_client:
        return None
    data = await redis_client.get(f"srch:{short_id}")
    if data:
        import json
        return json.loads(data)
    return None


async def get_cache(query: str) -> Optional[list[dict]]:
    if not redis_client:
        return None
    data = await redis_client.get(_cache_key(query))
    if data:
        import json
        return json.loads(data)
    return None


async def set_cache(query: str, tracks: list[dict]):
    if not redis_client:
        return
    import json
    await redis_client.setex(
        _cache_key(query),
        settings.CACHE_TTL,
        json.dumps(tracks, ensure_ascii=False),
    )


async def check_rate_limit(user_id: int) -> bool:
    if not redis_client:
        return True
    minute = int(time.time()) // settings.RATE_LIMIT_WINDOW
    key = f"ratelimit:{user_id}:{minute}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, settings.RATE_LIMIT_WINDOW)
    return count <= settings.RATE_LIMIT


async def is_banned(user_id: int) -> bool:
    if not redis_client:
        return True
    return await redis_client.exists(f"banned:{user_id}") > 0


async def add_to_history(user_id: int, query: str):
    if not redis_client:
        return
    key = f"history:{user_id}"
    await redis_client.lpush(key, query)
    await redis_client.ltrim(key, 0, 49)


async def get_history(user_id: int, limit: int = 10) -> list[str]:
    if not redis_client:
        return []
    return await redis_client.lrange(f"history:{user_id}", 0, limit - 1)
