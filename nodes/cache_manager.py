import threading
import time
from collections import OrderedDict
from typing import Any, Optional

class CacheEntry:

    __slots__ = ('data', 'timestamp', 'ttl', 'ref_count')

    def __init__(self, data: Any, ttl: int):
        self.data = data
        self.timestamp = time.monotonic()
        self.ttl = ttl
        self.ref_count = 1

    def is_expired(self) -> bool:
        return (time.monotonic() - self.timestamp) > self.ttl

class DistributedCache:

    def __init__(self, max_entries: int = 1000, ttl_seconds: int = 300):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._gc_collected = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            entry.ref_count += 1
            self._cache.move_to_end(key)
            return entry.data

    def put(self, key: str, data: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = CacheEntry(data, self._ttl_seconds)
            self._evict_if_needed()

    def invalidate(self, key: str) -> bool:
        with self._lock:
            return self._cache.pop(key, None) is not None

    def invalidate_all(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def gc_sweep(self) -> int:
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items() if v.is_expired()
            ]
            for k in expired_keys:
                del self._cache[k]
            self._gc_collected += len(expired_keys)
            return len(expired_keys)

    def _evict_if_needed(self) -> None:
        while len(self._cache) > self._max_entries:
            self._cache.popitem(last=False)

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return round(self._hits / total, 4) if total > 0 else 0.0

    def get_stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "entries": len(self._cache),
                "max_entries": self._max_entries,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self.hit_rate,
                "total_requests": total,
                "gc_collected": self._gc_collected,
            }
