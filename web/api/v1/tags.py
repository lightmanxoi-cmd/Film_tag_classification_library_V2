"""
API v1 标签路由模块

提供标签相关的RESTful API接口。

路由列表：
    GET    /tags/tree           # 获取标签树结构
    GET    /tags/<tag_id>/videos  # 获取标签下的视频列表

功能特点：
    - 支持层级标签结构
    - 自动计算标签下的视频数量
    - 查询结果缓存

使用示例：
    # 获取标签树
    GET /api/v1/tags/tree
    
    # 获取标签下的视频
    GET /api/v1/tags/1/videos?page=1&page_size=50

标签树结构：
    [
        {
            "id": 1,
            "name": "类型",
            "parent_id": null,
            "level": 0,
            "children": [
                {
                    "id": 2,
                    "name": "动作",
                    "parent_id": 1,
                    "level": 1,
                    "video_count": 10
                }
            ]
        }
    ]
"""
import os
from flask import Blueprint, request, g

from web.auth.decorators import login_required
from web.core.responses import APIResponse
from web.core.errors import handle_exceptions
from video_tag_system.utils.cache import get_cache, CACHE_KEYS

tags_bp = Blueprint('tags', __name__, url_prefix='/tags')


def get_services():
    """
    获取服务实例
    
    Returns:
        tuple: (video_service, tag_service, video_tag_service, db_session)
    """
    from web.services import get_services as _get_services
    return _get_services()


@tags_bp.route('/tree', methods=['GET'])
@login_required
@handle_exceptions
def get_tag_tree():
    """
    获取标签树
    
    返回层级结构的标签树，包含每个标签下的视频数量。
    结果会被缓存以提高性能。
    
    Returns:
        JSON响应，包含标签树结构
    
    Response Structure:
        [
            {
                "id": 1,
                "name": "类型",
                "parent_id": null,
                "description": "视频类型分类",
                "sort_order": 0,
                "level": 0,
                "children": [
                    {
                        "id": 2,
                        "name": "动作",
                        "parent_id": 1,
                        "level": 1,
                        "video_count": 10
                    }
                ]
            }
        ]
    
    Example:
        GET /api/v1/tags/tree
    """
    cache = get_cache()
    cache_key = CACHE_KEYS['tag_tree']
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return APIResponse.success(data=cached_result, cached=True)
    
    video_svc, tag_svc, video_tag_svc, _ = get_services()
    
    tree = tag_svc.get_tag_tree()
    result = []
    for item in tree.items:
        tag_data = {
            'id': item.id,
            'name': item.name,
            'parent_id': item.parent_id,
            'description': item.description,
            'sort_order': item.sort_order,
            'level': item.level,
            'children': []
        }
        for child in item.children:
            video_count = video_tag_svc.get_tag_video_count(child.id)
            tag_data['children'].append({
                'id': child.id,
                'name': child.name,
                'parent_id': child.parent_id,
                'description': child.description,
                'sort_order': child.sort_order,
                'level': child.level,
                'video_count': video_count
            })
        result.append(tag_data)
    
    cache.set(cache_key, result, ttl=120)
    return APIResponse.success(data=result, cached=False)


@tags_bp.route('/<int:tag_id>/videos', methods=['GET'])
@login_required
@handle_exceptions
def get_videos_by_tag(tag_id):
    """
    根据标签获取视频列表
    
    返回指定标签下的所有视频，支持分页。
    
    Args:
        tag_id: 标签ID
    
    Query Parameters:
        page: 页码，默认1
        page_size: 每页数量，默认50
    
    Returns:
        JSON响应，包含视频列表和分页信息
    
    Example:
        GET /api/v1/tags/1/videos?page=1&page_size=20
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    
    cache = get_cache()
    cache_key = f"videos:tag:{tag_id}:page:{page}:size:{page_size}"
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return APIResponse.success(data=cached_result, cached=True)
    
    video_svc, tag_svc, video_tag_svc, _ = get_services()
    
    result = video_svc.list_videos_by_tags(
        tag_ids=[tag_id],
        page=page,
        page_size=page_size,
        match_all=False
    )
    
    from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator
    thumbnail_gen = get_thumbnail_generator()
    
    videos = []
    for v in result.items:
        video_title = v.title or os.path.basename(v.file_path)
        videos.append({
            'id': v.id,
            'title': video_title,
            'file_path': v.file_path,
            'duration': v.duration,
            'tags': [{'id': t.id, 'name': t.name, 'parent_id': t.parent_id} for t in v.tags],
            'thumbnail': thumbnail_gen.get_thumbnail_url(video_title),
            'gif': thumbnail_gen.get_gif_url(video_title)
        })
    
    response_data = {
        'videos': videos,
        'total': result.total,
        'page': result.page,
        'page_size': result.page_size,
        'total_pages': result.total_pages
    }
    
    cache.set(cache_key, response_data, ttl=60)
    return APIResponse.success(data=response_data, cached=False)
