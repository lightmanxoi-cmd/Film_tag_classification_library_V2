"""
查询缓存模块

用于缓存频繁访问的数据，减少数据库查询次数，提升系统性能。
支持LRU（最近最少使用）淘汰策略、内存限制、自动清理过期条目。

主要组件：
    - LRUCache: 带LRU淘汰策略的线程安全缓存实现
    - QueryCache: 查询缓存封装类（兼容旧接口）
    - cached: 函数缓存装饰器
    - cached_method: 方法缓存装饰器

使用示例：
    # 直接使用缓存
    cache = get_cache()
    cache.set("user:1", user_data, ttl=300)
    data = cache.get("user:1")
    
    # 使用装饰器缓存函数结果
    @cached("user", ttl=60)
    def get_user(user_id):
        return db.query(User).get(user_id)

性能特点：
    - 线程安全：使用可重入锁保护并发访问
    - 内存控制：限制缓存使用的最大内存
    - 自动淘汰：LRU策略自动清理最少使用的条目
    - 过期清理：自动清理过期的缓存条目

Attributes:
    query_cache: 全局查询缓存实例
    CACHE_KEYS: 缓存键名常量字典
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
    """
    缓存条目数据类
    
    存储缓存值的元数据，包括过期时间、创建时间、大小等信息。
    使用泛型支持任意类型的缓存值。
    
    Attributes:
        value: 缓存的值
        expire_at: 过期时间戳（秒）
        created_at: 创建时间戳（秒）
        size: 估计的内存大小（字节）
        access_count: 访问次数统计
        last_access: 最后访问时间戳（秒）
    
    Example:
        entry = CacheEntry(
            value={"id": 1, "name": "test"},
            expire_at=time.time() + 300,
            created_at=time.time(),
            size=1024
        )
    """
    value: T
    expire_at: float
    created_at: float
    size: int = 0
    access_count: int = 0
    last_access: float = field(default_factory=time.time)


class LRUCache:
    """
    带LRU淘汰策略的线程安全缓存
    
    实现基于OrderedDict的LRU缓存，支持以下特性：
    1. 线程安全：使用可重入锁保护所有操作
    2. 容量限制：限制最大缓存条目数
    3. 内存限制：限制缓存使用的最大内存
    4. TTL过期：支持设置条目的生存时间
    5. 统计信息：记录命中率、淘汰次数等
    
    LRU淘汰策略：
    - 当缓存达到容量上限时，删除最久未使用的条目
    - 每次访问条目时，将其移到队列末尾（最近使用）
    - 队列头部是最久未使用的条目
    
    Attributes:
        _cache: 有序字典存储缓存条目
        _lock: 可重入锁保证线程安全
        _default_ttl: 默认的生存时间（秒）
        _max_size: 最大缓存条目数
        _max_memory: 最大内存使用量（字节）
        _current_memory: 当前内存使用量（字节）
        _stats: 统计信息字典
    
    Example:
        cache = LRUCache(max_size=1000, max_memory_mb=100, default_ttl=60)
        cache.set("key", {"data": "value"}, ttl=120)
        data = cache.get("key")
        stats = cache.get_stats()
    """
    
    def __init__(
        self, 
        max_size: int = 1000,
        max_memory_mb: int = 100,
        default_ttl: int = 60
    ):
        """
        初始化LRU缓存
        
        Args:
            max_size: 最大缓存条目数，默认1000
            max_memory_mb: 最大内存使用量（MB），默认100MB
            default_ttl: 默认生存时间（秒），默认60秒
        """
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
        """
        估计对象的内存大小
        
        使用sys.getsizeof估计对象占用的内存大小。
        如果无法获取大小，返回默认值1024字节。
        
        Args:
            obj: 要估计大小的对象
        
        Returns:
            int: 估计的内存大小（字节）
        """
        try:
            return sys.getsizeof(obj)
        except Exception:
            return 1024
    
    def _evict_lru(self) -> None:
        """
        执行LRU淘汰
        
        当缓存条目数达到上限时，删除最久未使用的条目。
        从OrderedDict的头部开始删除（头部是最久未使用的）。
        
        淘汰过程中更新统计信息和内存使用量。
        """
        while len(self._cache) >= self._max_size:
            oldest_key = next(iter(self._cache))
            entry = self._cache[oldest_key]
            self._current_memory -= entry.size
            del self._cache[oldest_key]
            self._stats["evictions"] += 1
    
    def _evict_memory(self, required: int) -> None:
        """
        执行内存淘汰
        
        当添加新条目会导致内存超限时，删除最久未使用的条目。
        持续删除直到有足够的内存空间。
        
        Args:
            required: 需要的内存大小（字节）
        """
        while self._current_memory + required > self._max_memory and self._cache:
            oldest_key = next(iter(self._cache))
            entry = self._cache[oldest_key]
            self._current_memory -= entry.size
            del self._cache[oldest_key]
            self._stats["memory_evictions"] += 1
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        从缓存中获取指定键的值。如果存在且未过期，返回值并更新访问统计。
        如果不存在或已过期，返回None。
        
        获取成功时会：
        1. 将条目移到队列末尾（标记为最近使用）
        2. 增加访问计数
        3. 更新最后访问时间
        
        Args:
            key: 缓存键
        
        Returns:
            Optional[Any]: 缓存值，不存在或过期时返回None
        """
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
        """
        设置缓存值
        
        将值存入缓存，设置过期时间。如果键已存在，更新值和过期时间。
        在设置前会检查内存限制和容量限制，必要时执行淘汰。
        
        注意：如果单个值的大小超过最大内存的50%，则不会缓存该值。
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None则使用默认值
        """
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
        """
        删除缓存条目
        
        从缓存中删除指定键的条目。
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 删除成功返回True，键不存在返回False
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                self._current_memory -= entry.size
                del self._cache[key]
                return True
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        按前缀模式删除缓存条目
        
        删除所有以指定前缀开头的缓存条目。
        常用于批量清除相关缓存，如清除某个实体的所有缓存。
        
        Args:
            pattern: 缓存键前缀模式
        
        Returns:
            int: 删除的条目数量
        
        Example:
            # 删除所有用户相关缓存
            deleted_count = cache.delete_pattern("user:")
        """
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
        """
        清空缓存
        
        删除所有缓存条目，重置内存使用量。
        """
        with self._lock:
            self._cache.clear()
            self._current_memory = 0
    
    def cleanup_expired(self) -> int:
        """
        清理过期条目
        
        遍历缓存，删除所有已过期的条目。
        建议定期调用此方法清理过期数据。
        
        Returns:
            int: 清理的条目数量
        """
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
        """
        获取缓存统计信息
        
        返回缓存的运行状态统计，包括：
        - hits: 缓存命中次数
        - misses: 缓存未命中次数
        - hit_rate: 缓存命中率
        - cache_size: 当前缓存条目数
        - memory_usage_mb: 当前内存使用量（MB）
        - evictions: 容量淘汰次数
        - memory_evictions: 内存淘汰次数
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
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
        """
        获取当前内存使用量
        
        Returns:
            int: 当前内存使用量（字节）
        """
        return self._current_memory


class QueryCache:
    """
    线程安全的查询缓存
    
    封装LRUCache，提供兼容旧接口的查询缓存功能。
    主要用于缓存数据库查询结果，减少重复查询。
    
    默认配置：
    - 最大条目数：2000
    - 最大内存：100MB
    - 默认TTL：60秒
    
    Attributes:
        _lru_cache: 内部LRU缓存实例
    
    Example:
        cache = QueryCache(default_ttl=120)
        cache.set("videos:all", video_list, ttl=300)
        videos = cache.get("videos:all")
    """
    
    def __init__(self, default_ttl: int = 60):
        """
        初始化查询缓存
        
        Args:
            default_ttl: 默认生存时间（秒），默认60秒
        """
        self._lru_cache = LRUCache(
            max_size=2000,
            max_memory_mb=100,
            default_ttl=default_ttl
        )
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
        
        Returns:
            Optional[Any]: 缓存值，不存在时返回None
        """
        return self._lru_cache.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None则使用默认值
        """
        self._lru_cache.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """
        删除缓存条目
        
        Args:
            key: 缓存键
        
        Returns:
            bool: 删除成功返回True
        """
        return self._lru_cache.delete(key)
    
    def delete_pattern(self, pattern: str) -> int:
        """
        按前缀模式删除缓存条目
        
        Args:
            pattern: 缓存键前缀模式
        
        Returns:
            int: 删除的条目数量
        """
        return self._lru_cache.delete_pattern(pattern)
    
    def clear(self) -> None:
        """
        清空缓存
        """
        self._lru_cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        清理过期条目
        
        Returns:
            int: 清理的条目数量
        """
        return self._lru_cache.cleanup_expired()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        return self._lru_cache.get_stats()


def cached(key_prefix: str, ttl: int = 60):
    """
    函数缓存装饰器
    
    用于缓存函数的返回值，避免重复计算或查询。
    根据函数参数生成缓存键，相同参数直接返回缓存结果。
    
    缓存键格式：{key_prefix}:{参数哈希值}
    
    Args:
        key_prefix: 缓存键前缀，用于标识缓存类型
        ttl: 生存时间（秒），默认60秒
    
    Returns:
        Callable: 装饰器函数
    
    Example:
        @cached("user", ttl=120)
        def get_user_by_id(user_id: int):
            return db.query(User).get(user_id)
        
        # 第一次调用会执行函数并缓存结果
        user = get_user_by_id(1)
        # 第二次调用直接返回缓存结果
        user = get_user_by_id(1)
    """
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
    """
    使缓存失效
    
    删除指定前缀的所有缓存条目。
    常用于数据更新后清除相关缓存。
    
    Args:
        key_prefix: 缓存键前缀
    
    Returns:
        int: 删除的条目数量
    
    Example:
        # 更新用户后清除用户相关缓存
        update_user(user_id, data)
        invalidate_cache("user")
    """
    return query_cache.delete_pattern(key_prefix)


def cached_method(key_prefix: str, ttl: int = 60):
    """
    方法缓存装饰器
    
    用于缓存类方法的返回值。与cached装饰器类似，
    但支持类方法的self参数，将方法名包含在缓存键中。
    
    缓存键格式：{key_prefix}:{方法名}:{参数哈希值}
    
    Args:
        key_prefix: 缓存键前缀
        ttl: 生存时间（秒），默认60秒
    
    Returns:
        Callable: 装饰器函数
    
    Example:
        class UserService:
            @cached_method("user_service", ttl=120)
            def get_user(self, user_id: int):
                return self.repo.get(user_id)
    """
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
    """
    获取全局查询缓存实例
    
    返回全局的QueryCache实例，用于统一管理缓存。
    
    Returns:
        QueryCache: 全局查询缓存实例
    
    Example:
        cache = get_cache()
        cache.set("key", "value")
        value = cache.get("key")
    """
    return query_cache
