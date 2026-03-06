"""
API v1 缓存路由
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
    """获取缓存统计"""
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
    """清除所有缓存"""
    cache = get_cache()
    cache.clear()
    
    return APIResponse.success(message='缓存清除成功')


@cache_bp.route('/invalidate/<key_prefix>', methods=['POST'])
@login_required
def invalidate_cache(key_prefix):
    """使指定前缀的缓存失效"""
    cache = get_cache()
    count = cache.delete_pattern(key_prefix)
    
    return APIResponse.success(
        message=f'已使 {count} 个缓存条目失效',
        data={'count': count}
    )
