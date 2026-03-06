"""
API v1 统计路由
"""
from flask import Blueprint

from web.auth.decorators import login_required
from web.core.responses import APIResponse
from web.core.errors import handle_exceptions
from video_tag_system.utils.cache import get_cache, CACHE_KEYS

stats_bp = Blueprint('stats', __name__, url_prefix='/stats')


def get_services():
    """获取服务实例"""
    from web.services import get_services as _get_services
    return _get_services()


@stats_bp.route('', methods=['GET'])
@login_required
@handle_exceptions
def get_stats():
    """获取统计数据"""
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
