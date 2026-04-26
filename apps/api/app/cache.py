"""TTL cache helper. Klucze typu str, wartości dowolne. Współdzielone między requestami."""
from __future__ import annotations

import time
from threading import RLock
from typing import Any, Callable

from .deps import get_settings


class TTLCache:
    def __init__(self, ttl_seconds: int = 60, maxsize: int = 256):
        self._ttl = ttl_seconds
        self._max = maxsize
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            row = self._store.get(key)
            if not row:
                return None
            expiry, val = row
            if expiry < time.time():
                self._store.pop(key, None)
                return None
            return val

    def set(self, key: str, val: Any) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                # Drop najstarszy expiry
                oldest = min(self._store.items(), key=lambda kv: kv[1][0])[0]
                self._store.pop(oldest, None)
            self._store[key] = (time.time() + self._ttl, val)

    def invalidate(self, prefix: str | None = None) -> int:
        with self._lock:
            if prefix is None:
                n = len(self._store)
                self._store.clear()
                return n
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                self._store.pop(k, None)
            return len(keys)


_settings = get_settings()
_default = TTLCache(ttl_seconds=_settings.CACHE_TTL_SECONDS)


def cache() -> TTLCache:
    return _default


def cached(key_builder: Callable[..., str]):
    """Dekorator: cache po kluczu zbudowanym z args funkcji."""
    def deco(fn: Callable):
        def wrap(*args, **kwargs):
            key = key_builder(*args, **kwargs)
            hit = _default.get(key)
            if hit is not None:
                return hit
            val = fn(*args, **kwargs)
            _default.set(key, val)
            return val
        return wrap
    return deco
