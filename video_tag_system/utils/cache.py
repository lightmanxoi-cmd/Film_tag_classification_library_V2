"""
查询缓存模块
用于缓存频繁访问的数据，减少数据库查询
"""
import threading
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Generic
from dataclasses import dataclass

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expire_at: float
    created_at: float


class QueryCache:
    """Thread-safe查询缓存"""
    
    def __init__(self, default_ttl: int = 60):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
        self._stats = {
            "hits": 0,
            "misses": 0,
        }
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None
            
            if time.time() > entry.expire_at:
                del self._cache[key]
                self._stats["misses"] += 1
                return None
            
            self._stats["hits"] += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            now = time.time()
            expire_at = now + (ttl if ttl is not None else self._default_ttl)
            self._cache[key] = CacheEntry(
                value=value,
                expire_at=expire_at,
                created_at=now
            )
    
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        count = 0
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern)]
            for key in keys_to_delete:
                del self._cache[key]
                count += 1
        return count
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> int:
        count = 0
        with self._lock:
            now = time.time()
            keys_to_delete = [
                k for k, v in self._cache.items() 
                if v.expire_at < now
            ]
            for key in keys_to_delete:
                del self._cache[key]
                count += 1
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total if total > 0 else 0
            return {
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate": f"{hit_rate:.2%}",
                "cache_size": len(self._cache),
            }


def cached(key_prefix: str, ttl: int = 60):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            cached_value = query_cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            query_cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


def invalidate_cache(key_prefix: str) -> int:
    return query_cache.delete_pattern(key_prefix)


query_cache = QueryCache(default_ttl=60)


CACHE_KEYS = {
    "tag_tree": "tag:tree",
    "tag_by_id": "tag:by_id",
    "video_count": "video:count",
    "tag_video_count": "tag:video_count",
    "video_by_id": "video:by_id",
}
