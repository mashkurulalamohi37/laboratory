"""Read-through JSON cache on Redis with namespace versioning.

Redis is never a source of truth: every cache failure degrades to a cache miss, so an
unavailable Redis slows responses down but never breaks them. A namespace (for example
`catalog`) carries a version number; bumping it after a commit makes every key written
under the old version unreachable at once, which is how publish invalidates search caches.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from redis.exceptions import RedisError

from app.core.logging import get_logger
from app.core.redis import get_redis

log = get_logger(__name__)


#: Public search and autocomplete results (catalog + centres). Bumped after any change.
SEARCH_NAMESPACE = "search"


def _version_key(namespace: str) -> str:
    return f"cache-version:{namespace}"


async def namespace_version(namespace: str) -> str:
    try:
        return str(await get_redis().get(_version_key(namespace)) or "0")
    except (RedisError, OSError):
        return "unavailable"


async def bump_namespace(namespace: str) -> None:
    try:
        await get_redis().incr(_version_key(namespace))
    except (RedisError, OSError):
        log.warning("cache_bump_failed", namespace=namespace)


async def cached_json(
    namespace: str, key: str, ttl_seconds: int, compute: Callable[[], Awaitable[Any]]
) -> Any:
    """Return the cached value for `key`, computing and storing it on a miss."""
    version = await namespace_version(namespace)
    if version == "unavailable":
        return await compute()
    full_key = f"cache:{namespace}:v{version}:{key}"
    redis = get_redis()
    try:
        hit = await redis.get(full_key)
    except (RedisError, OSError):
        hit = None
    if hit is not None:
        return json.loads(hit)
    value = await compute()
    try:
        await redis.set(full_key, json.dumps(value, default=str), ex=ttl_seconds)
    except (RedisError, OSError):
        log.warning("cache_store_failed", namespace=namespace)
    return value
