"""
redis_cache.py — Async Redis wrapper for recommendation caching.

Key strategy:
  rec:{variant}:{visitor_id}  → JSON recommendations  (TTL: 5 min)
  popular:items               → JSON popular fallback  (TTL: 30 min)
"""

import json
import logging
from typing import Any, Optional
import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            await _redis.ping()
            logger.info("Redis connection established")
        except Exception as exc:
            logger.warning(f"Redis unavailable — caching disabled: {exc}")
            _redis = None
    return _redis


async def cache_get(key: str) -> Optional[Any]:
    """Return deserialized value or None on miss/error."""
    try:
        r = await get_redis()
        if r is None:
            return None
        raw = await r.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.debug(f"Cache GET error [{key}]: {exc}")
        return None


async def cache_set(key: str, value: Any, ttl: int = None) -> bool:
    """Serialize and store value with TTL. Returns success flag."""
    try:
        r = await get_redis()
        if r is None:
            return False
        ttl = ttl or settings.REDIS_CACHE_TTL
        await r.setex(key, ttl, json.dumps(value))
        return True
    except Exception as exc:
        logger.debug(f"Cache SET error [{key}]: {exc}")
        return False


async def cache_delete(*keys: str) -> None:
    """Delete one or more keys."""
    try:
        r = await get_redis()
        if r and keys:
            await r.delete(*keys)
    except Exception as exc:
        logger.debug(f"Cache DELETE error {keys}: {exc}")


async def cache_flush_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count deleted."""
    try:
        r = await get_redis()
        if r is None:
            return 0
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)
        return len(keys)
    except Exception as exc:
        logger.debug(f"Cache flush error [{pattern}]: {exc}")
        return 0


def rec_cache_key(visitor_id: str, variant: str) -> str:
    return f"rec:{variant}:{visitor_id}"


def popular_cache_key() -> str:
    return "popular:items"
