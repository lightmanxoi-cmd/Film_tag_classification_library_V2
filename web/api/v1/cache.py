"""
API v1 缓存路由模块

提供缓存管理相关的RESTful API接口。

路由列表：
    GET    /cache/stats               # 获取缓存统计信息
    POST   /cache/clear               # 清除所有缓存
    POST   /cache/invalidate/<prefix> # 使指定前缀的缓存失效

功能特点：
    - 查询缓存统计信息
    - 清除所有缓存
    - 按前缀批量失效缓存

使用示例：
    # 获取缓存统计
    GET /api/v1/cache/stats
    
    # 清除所有缓存
    POST /api/v1/cache/clear
    
    # 使指定前缀缓存失效
    POST /api/v1/cache/invalidate/videos

缓存类型：
    - query_cache: 查询结果缓存
    - thumbnail_cache: 缩略图缓存

注意：
    清除缓存会影响系统性能，建议在数据更新后使用。
"""
from flask import Blueprint, request

from web.auth.decorators import login_required
from web.core.responses import APIResponse
from video_tag_system.utils.cache import get_cache, query_cache
from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator

cache_bp = Blueprint('cache', __name__, url_prefix='/cache')


@cache_bp.route('/stats', methods=['GET'])
@login_required
def get_cache_stats():
    """
    获取缓存统计信息
    
    返回查询缓存和缩略图缓存的统计信息。
    
    Returns:
        JSON响应，包含缓存统计信息
    
    Response Structure:
        {
            "query_cache": {
                "size": 100,
                "max_size": 1000,
                "hits": 5000,
                "misses": 200
            },
            "thumbnail_cache": {
                "thumbnails": 50,
                "gifs": 20
            }
        }
    
    Example:
        GET /api/v1/cache/stats
    """
    cache = get_cache()
    thumbnail_gen = get_thumbnail_generator()
    
    query_stats = cache.get_stats()
    thumbnail_stats = thumbnail_gen.get_cache_stats()
    
    return APIResponse.success(data={
        'query_cache': query_stats,
        'thumbnail_cache': thumbnail_stats
    })


@cache_bp.route('/clear', methods=['POST'])
@login_required
def clear_cache():
    """
    清除所有缓存
    
    清除查询缓存中的所有条目。
    注意：这会影响系统性能，建议在数据大量更新后使用。
    
    Returns:
        JSON响应，确认缓存已清除
    
    Example:
        POST /api/v1/cache/clear
        {
            "success": true,
            "message": "缓存清除成功"
        }
    """
    cache = get_cache()
    cache.clear()
    
    return APIResponse.success(message='缓存清除成功')


@cache_bp.route('/invalidate/<key_prefix>', methods=['POST'])
@login_required
def invalidate_cache(key_prefix):
    """
    使指定前缀的缓存失效
    
    批量删除指定前缀的所有缓存条目。
    常用前缀：
        - videos: 视频相关缓存
        - tags: 标签相关缓存
        - stats: 统计数据缓存
    
    Args:
        key_prefix: 缓存键前缀
    
    Returns:
        JSON响应，包含失效的缓存条目数量
    
    Example:
        POST /api/v1/cache/invalidate/videos
        {
            "success": true,
            "message": "已使 10 个缓存条目失效",
            "data": {
                "count": 10
            }
        }
    """
    cache = get_cache()
    count = cache.delete_pattern(key_prefix)
    
    return APIResponse.success(
        message=f'已使 {count} 个缓存条目失效',
        data={'count': count}
    )
