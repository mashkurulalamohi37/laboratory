"""Fixed-window rate limiting backed by Redis (application-level, per phone/user/IP).

Nginx applies coarse per-IP limits at the edge; this layer protects sensitive
operations such as OTP sending, login and report retrieval.
"""

from __future__ import annotations

from app.core.errors import RateLimited
from app.core.redis import get_redis


async def hit(key: str, *, limit: int, window_seconds: int) -> int:
    """Count one hit; raise `RateLimited` once the window's limit is exceeded."""
    redis = get_redis()
    full_key = f"rl:{key}"
    async with redis.pipeline(transaction=True) as pipe:
        pipe.incr(full_key)
        pipe.expire(full_key, window_seconds, nx=True)
        pipe.ttl(full_key)
        count, _, ttl = await pipe.execute()
    if int(count) > limit:
        raise RateLimited(retry_after=int(ttl) if int(ttl) > 0 else window_seconds)
    return int(count)


async def reset(key: str) -> None:
    await get_redis().delete(f"rl:{key}")
