"""In-memory schema cache with TTL for performance (avoid repeated DB introspection)."""
import time
from typing import Optional

_schema_cache: Optional[str] = None
_schema_cache_ts: float = 0.0


def get_cached_schema(ttl_seconds: int) -> Optional[str]:
    """Return cached schema if still valid. ttl_seconds <= 0 means no cache."""
    if ttl_seconds <= 0:
        return None
    global _schema_cache, _schema_cache_ts
    if _schema_cache is not None and (time.monotonic() - _schema_cache_ts) < ttl_seconds:
        return _schema_cache
    return None


def set_cached_schema(schema: str, ttl_seconds: int = 300) -> None:
    """Store schema in cache. Only stores if ttl_seconds > 0."""
    if ttl_seconds <= 0:
        return
    global _schema_cache, _schema_cache_ts
    _schema_cache = schema
    _schema_cache_ts = time.monotonic()
