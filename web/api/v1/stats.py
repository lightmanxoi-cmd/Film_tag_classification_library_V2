"""
API v1 统计路由模块

提供系统统计数据相关的RESTful API接口。

路由列表：
    GET    /stats           # 获取系统统计数据
    GET    /stats/metrics   # 获取性能指标数据

功能特点：
    - 视频总数统计
    - 标签总数统计
    - 性能指标收集
    - 查询结果缓存

使用示例：
    GET /api/v1/stats
    GET /api/v1/stats/metrics

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
from web.services import ServiceLocator
from video_tag_system.utils.cache import get_cache, CACHE_KEYS
from video_tag_system.utils.logger import metrics, get_logger
from web.core.cache_decorator import get_cached_or_fetch

logger = get_logger(__name__)
stats_bp = Blueprint('stats', __name__, url_prefix='/stats')


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
    cache_key = CACHE_KEYS['stats']
    
    video_svc = ServiceLocator.get_video_service()
    tag_svc = ServiceLocator.get_tag_service()
    
    data, is_cached = get_cached_or_fetch(
        cache_key=cache_key,
        fetch_func=lambda: {
            'video_count': video_svc.count_videos(),
            'tag_count': tag_svc.count_tags()
        },
        ttl=60
    )
    return APIResponse.success(data=data, cached=is_cached)


@stats_bp.route('/metrics', methods=['GET'])
@login_required
@handle_exceptions
def get_metrics():
    """
    获取性能指标
    
    返回系统收集的性能指标数据，包括函数执行时间等。
    
    Returns:
        JSON响应，包含性能指标
    
    Response Structure:
        {
            "success": true,
            "data": {
                "metrics": {
                    "function_name": [
                        {"value": 0.123, "timestamp": "...", "tags": {}}
                    ]
                }
            }
        }
    
    Example:
        GET /api/v1/stats/metrics
    """
    all_metrics = metrics.get_metrics()
    
    summary = {}
    for metric_name, values in all_metrics.items():
        if values:
            recent_values = [v['value'] for v in values[-100:]]
            summary[metric_name] = {
                'count': len(values),
                'recent_count': len(recent_values),
                'avg': sum(recent_values) / len(recent_values) if recent_values else 0,
                'min': min(recent_values) if recent_values else 0,
                'max': max(recent_values) if recent_values else 0,
                'last': recent_values[-1] if recent_values else 0
            }
    
    cache = get_cache()
    cache_stats = cache.get_stats()
    
    return APIResponse.success(data={
        'summary': summary,
        'raw_metrics': {k: v[-20:] for k, v in all_metrics.items() if v},
        'cache': cache_stats
    })


@stats_bp.route('/metrics/clear', methods=['POST'])
@login_required
@handle_exceptions
def clear_metrics():
    """
    清除性能指标
    
    清除所有收集的性能指标数据。
    
    Returns:
        JSON响应，确认清除操作
    
    Example:
        POST /api/v1/stats/metrics/clear
    """
    metrics.clear()
    logger.info("性能指标已清除")
    return APIResponse.success(message='性能指标已清除')
