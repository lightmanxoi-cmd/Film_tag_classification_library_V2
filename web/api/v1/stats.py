"""
API v1 统计路由模块

提供系统统计数据相关的RESTful API接口。

路由列表：
    GET    /stats    # 获取系统统计数据

功能特点：
    - 视频总数统计
    - 标签总数统计
    - 查询结果缓存

使用示例：
    GET /api/v1/stats

响应结构：
    {
        "success": true,
        "data": {
            "video_count": 1000,
            "tag_count": 50
        }
    }
"""
from flask import Blueprint

from web.auth.decorators import login_required
from web.core.responses import APIResponse
from web.core.errors import handle_exceptions
from video_tag_system.utils.cache import get_cache, CACHE_KEYS

stats_bp = Blueprint('stats', __name__, url_prefix='/stats')


def get_services():
    """
    获取服务实例
    
    Returns:
        tuple: (video_service, tag_service, video_tag_service, db_session)
    """
    from web.services import get_services as _get_services
    return _get_services()


@stats_bp.route('', methods=['GET'])
@login_required
@handle_exceptions
def get_stats():
    """
    获取统计数据
    
    返回系统的统计数据，包括视频总数和标签总数。
    结果会被缓存以提高性能。
    
    Returns:
        JSON响应，包含统计数据
    
    Response Structure:
        {
            "success": true,
            "data": {
                "video_count": 1000,
                "tag_count": 50
            },
            "cached": false
        }
    
    Example:
        GET /api/v1/stats
    """
    cache = get_cache()
    cache_key = CACHE_KEYS['stats']
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return APIResponse.success(data=cached_result, cached=True)
    
    video_svc, tag_svc, _, _ = get_services()
    
    video_count = video_svc.count_videos()
    tag_count = tag_svc.count_tags()
    
    result = {
        'video_count': video_count,
        'tag_count': tag_count
    }
    
    cache.set(cache_key, result, ttl=60)
    return APIResponse.success(data=result, cached=False)
