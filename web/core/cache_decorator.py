from functools import wraps
from typing import Optional, Callable, Any, Tuple
from flask import request

from web.core.responses import APIResponse
from video_tag_system.utils.cache import get_cache


def cached_view(key_func: Callable, ttl: int = 60):
    """
    API端点缓存装饰器

    自动处理缓存读取和写入，减少重复的缓存操作代码。

    被装饰的函数应返回一个可序列化的dict作为response data，
    装饰器会自动包装成APIResponse.success()响应。

    Args:
        key_func: 接收与被装饰函数相同参数的缓存键生成函数
        ttl: 缓存生存时间（秒），默认60

    Example:
        def _videos_cache_key(page, page_size, **kwargs):
            return f"videos:list:page:{page}:size:{page_size}"

        @videos_bp.route('', methods=['GET'])
        @login_required
        @cached_view(key_func=_videos_cache_key, ttl=60)
        def get_videos():
            # 只需返回response_data，无需处理缓存
            result = video_svc.list_videos(...)
            return serialize_paginated_videos(result)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache = get_cache()
            cache_key = key_func(*args, **kwargs)

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return APIResponse.success(data=cached_result, cached=True)

            response_data = f(*args, **kwargs)

            cache.set(cache_key, response_data, ttl)
            return APIResponse.success(data=response_data, cached=False)

        return decorated_function
    return decorator


def get_cached_or_fetch(cache_key: str, fetch_func: Callable, ttl: int = 60) -> Tuple[Any, bool]:
    """
    缓存辅助函数：获取缓存或执行查询

    简化缓存检查模式，返回(数据, 是否缓存命中)的元组。

    Args:
        cache_key: 缓存键
        fetch_func: 缓存未命中时的数据获取函数
        ttl: 缓存生存时间（秒），默认60

    Returns:
        Tuple[Any, bool]: (数据, 是否缓存命中)

    Example:
        data, is_cached = get_cached_or_fetch(
            cache_key=f"videos:list:page:{page}",
            fetch_func=lambda: serialize_paginated_videos(result),
            ttl=60
        )
        return APIResponse.success(data=data, cached=is_cached)
    """
    cache = get_cache()

    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result, True

    data = fetch_func()
    cache.set(cache_key, data, ttl)
    return data, False
