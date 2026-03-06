"""
查询缓存模块
用于缓存频繁访问的数据，减少数据库查询
支持LRU淘汰策略、内存限制、自动清理
"""
import threading
import time
import sys
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Generic
from dataclasses import dataclass, field

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expire_at: float
    created_at: float
    size: int = 0
    access_count: int = 0
    last_access: float = field(default_factory=time.time)


class LRUCache:
    """带LRU淘汰策略的线程安全缓存"""
    
    def __init__(
        self, 
        max_size: int = 1000,
        max_memory_mb: int = 100,
        default_ttl: int = 60
    ):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._max_memory = max_memory_mb * 1024 * 1024
        self._current_memory = 0
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "memory_evictions": 0,
        }
        self._cleanup_interval = 300
        self._last_cleanup = time.time()
    
    def _estimate_size(self, obj: Any) -> int:
        try:
            return sys.getsizeof(obj)
        except Exception:
            return 1024
    
    def _evict_lru(self) -> None:
        while len(self._cache) >= self._max_size:
            oldest_key = next(iter(self._cache))
            entry = self._cache[oldest_key]
            self._current_memory -= entry.size
            del self._cache[oldest_key]
            self._stats["evictions"] += 1
    
    def _evict_memory(self, required: int) -> None:
        while self._current_memory + required > self._max_memory and self._cache:
            oldest_key = next(iter(self._cache))
            entry = self._cache[oldest_key]
            self._current_memory -= entry.size
            del self._cache[oldest_key]
            self._stats["memory_evictions"] += 1
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._stats["misses"] += 1
                return None
            
            if time.time() > entry.expire_at:
                self._current_memory -= entry.size
                del self._cache[key]
                self._stats["misses"] += 1
                return None
            
            self._cache.move_to_end(key)
            entry.access_count += 1
            entry.last_access = time.time()
            self._stats["hits"] += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            now = time.time()
            expire_at = now + (ttl if ttl is not None else self._default_ttl)
            size = self._estimate_size(value)
            
            if key in self._cache:
                old_entry = self._cache[key]
                self._current_memory -= old_entry.size
                del self._cache[key]
            
            if size > self._max_memory * 0.5:
                return
            
            self._evict_memory(size)
            self._evict_lru()
            
            self._cache[key] = CacheEntry(
                value=value,
                expire_at=expire_at,
                created_at=now,
                size=size,
                access_count=0,
                last_access=now
            )
            self._current_memory += size
    
    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._current_memory -= entry.size
                del self._cache[key]
                return True
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        count = 0
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern)]
            for key in keys_to_delete:
                entry = self._cache[key]
                self._current_memory -= entry.size
                del self._cache[key]
                count += 1
        return count
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._current_memory = 0
    
    def cleanup_expired(self) -> int:
        count = 0
        with self._lock:
            now = time.time()
            keys_to_delete = [
                k for k, v in self._cache.items() 
                if v.expire_at < now
            ]
            for key in keys_to_delete:
                entry = self._cache[key]
                self._current_memory -= entry.size
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
                "memory_usage_mb": round(self._current_memory / (1024 * 1024), 2),
                "evictions": self._stats["evictions"],
                "memory_evictions": self._stats["memory_evictions"],
            }
    
    def get_memory_usage(self) -> int:
        return self._current_memory


class QueryCache:
    """Thread-safe查询缓存（兼容旧接口）"""
    
    def __init__(self, default_ttl: int = 60):
        self._lru_cache = LRUCache(
            max_size=2000,
            max_memory_mb=100,
            default_ttl=default_ttl
        )
    
    def get(self, key: str) -> Optional[Any]:
        return self._lru_cache.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._lru_cache.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        return self._lru_cache.delete(key)
    
    def delete_pattern(self, pattern: str) -> int:
        return self._lru_cache.delete_pattern(pattern)
    
    def clear(self) -> None:
        self._lru_cache.clear()
    
    def cleanup_expired(self) -> int:
        return self._lru_cache.cleanup_expired()
    
    def get_stats(self) -> Dict[str, Any]:
        return self._lru_cache.get_stats()


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


def cached_method(key_prefix: str, ttl: int = 60):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            cached_value = query_cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = func(self, *args, **kwargs)
            query_cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


query_cache = QueryCache(default_ttl=60)


CACHE_KEYS = {
    "tag_tree": "tag:tree",
    "tag_by_id": "tag:by_id",
    "video_count": "video:count",
    "tag_video_count": "tag:video_count",
    "video_by_id": "video:by_id",
    "video_list": "video:list",
    "stats": "stats:overview",
    "thumbnail_url": "thumbnail:url",
    "gif_url": "gif:url",
}


def get_cache() -> QueryCache:
    return query_cache
