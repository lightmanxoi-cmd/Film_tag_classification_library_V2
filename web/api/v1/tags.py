"""
API v1 标签路由模块

提供标签相关的RESTful API接口。

路由列表：
    GET    /tags/tree           # 获取标签树结构
    GET    /tags/<tag_id>/videos  # 获取标签下的视频列表
    POST   /tags                # 创建标签
    PUT    /tags/<tag_id>       # 更新标签（重命名/修改层级）
    DELETE /tags/<tag_id>       # 删除标签
    POST   /tags/merge          # 合并标签

功能特点：
    - 支持层级标签结构
    - 自动计算标签下的视频数量
    - 查询结果缓存

使用示例：
    # 获取标签树
    GET /api/v1/tags/tree
    
    # 获取标签下的视频
    GET /api/v1/tags/1/videos?page=1&page_size=50
    
    # 创建标签
    POST /api/v1/tags
    {"name": "新标签", "parent_id": null}
    
    # 重命名标签
    PUT /api/v1/tags/1
    {"name": "新名称"}
    
    # 修改标签层级
    PUT /api/v1/tags/1
    {"parent_id": 2}
    
    # 删除标签
    DELETE /api/v1/tags/1
    
    # 合并标签
    POST /api/v1/tags/merge
    {"source_tag_id": 1, "target_tag_id": 2}

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
from web.services import ServiceLocator
from video_tag_system.utils.cache import get_cache, CACHE_KEYS
from video_tag_system.models.tag import TagCreate, TagUpdate, TagMergeRequest
from video_tag_system.exceptions import (
    TagNotFoundError,
    DuplicateTagError,
    ValidationError,
    TagMergeError
)

tags_bp = Blueprint('tags', __name__, url_prefix='/tags')


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
    
    tag_svc = ServiceLocator.get_tag_service()
    
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
    
    video_svc = ServiceLocator.get_video_service()
    
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


@tags_bp.route('', methods=['POST'])
@login_required
@handle_exceptions
def create_tag():
    """
    创建标签
    
    创建一级标签或二级标签。
    
    Request Body:
        name: 标签名称
        parent_id: 父标签ID（可选，创建二级标签时需要）
    
    Returns:
        JSON响应，包含创建的标签信息
    
    Example:
        POST /api/v1/tags
        {"name": "新标签"}
        
        POST /api/v1/tags
        {"name": "子标签", "parent_id": 1}
    """
    data = request.get_json()
    name = data.get('name', '').strip()
    parent_id = data.get('parent_id')
    
    if not name:
        return APIResponse.error('标签名称不能为空', status_code=400)
    
    tag_svc = ServiceLocator.get_tag_service()
    
    try:
        tag_data = TagCreate(name=name, parent_id=parent_id)
        tag = tag_svc.create_tag(tag_data)
        
        cache = get_cache()
        cache.delete(CACHE_KEYS['tag_tree'])
        
        return APIResponse.success(data={
            'id': tag.id,
            'name': tag.name,
            'parent_id': tag.parent_id,
            'level': tag.level
        })
    except (TagNotFoundError, DuplicateTagError, ValidationError) as e:
        return APIResponse.error(str(e), status_code=400)


@tags_bp.route('/<int:tag_id>', methods=['PUT'])
@login_required
@handle_exceptions
def update_tag(tag_id):
    """
    更新标签
    
    支持重命名和修改层级。
    
    Args:
        tag_id: 标签ID
    
    Request Body:
        name: 新名称（可选）
        parent_id: 新父标签ID（可选，null表示提升为一级标签）
    
    Returns:
        JSON响应，包含更新后的标签信息
    
    Example:
        PUT /api/v1/tags/1
        {"name": "新名称"}
        
        PUT /api/v1/tags/1
        {"parent_id": 2}
    """
    data = request.get_json()
    name = data.get('name')
    parent_id = data.get('parent_id')
    
    if name is not None:
        name = name.strip()
        if not name:
            return APIResponse.error('标签名称不能为空', status_code=400)
    
    tag_svc = ServiceLocator.get_tag_service()
    
    try:
        tag_data = TagUpdate(name=name, parent_id=parent_id)
        tag = tag_svc.update_tag(tag_id, tag_data)
        
        cache = get_cache()
        cache.delete(CACHE_KEYS['tag_tree'])
        
        return APIResponse.success(data={
            'id': tag.id,
            'name': tag.name,
            'parent_id': tag.parent_id,
            'level': tag.level
        })
    except (TagNotFoundError, DuplicateTagError, ValidationError) as e:
        return APIResponse.error(str(e), status_code=400)


@tags_bp.route('/<int:tag_id>', methods=['DELETE'])
@login_required
@handle_exceptions
def delete_tag(tag_id):
    """
    删除标签
    
    删除指定标签。如果标签有子标签，需要先删除子标签。
    
    Args:
        tag_id: 标签ID
    
    Returns:
        JSON响应
    
    Example:
        DELETE /api/v1/tags/1
    """
    tag_svc = ServiceLocator.get_tag_service()
    video_tag_svc = ServiceLocator.get_video_tag_service()
    
    try:
        video_count = video_tag_svc.get_tag_video_count(tag_id)
        tag = tag_svc.get_tag(tag_id)
        children_count = len(tag.children) if tag.children else 0
        
        if children_count > 0:
            return APIResponse.error(
                f'该标签下有 {children_count} 个子标签，请先删除或移动子标签',
                status_code=400
            )
        
        tag_svc.delete_tag(tag_id)
        
        cache = get_cache()
        cache.delete(CACHE_KEYS['tag_tree'])
        
        return APIResponse.success(data={
            'deleted_video_relations': video_count
        })
    except TagNotFoundError as e:
        return APIResponse.error(str(e), status_code=404)
    except ValidationError as e:
        return APIResponse.error(str(e), status_code=400)


@tags_bp.route('/merge', methods=['POST'])
@login_required
@handle_exceptions
def merge_tags():
    """
    合并标签
    
    将源标签的所有视频关联转移到目标标签，然后删除源标签。
    
    Request Body:
        source_tag_id: 源标签ID（将被删除）
        target_tag_id: 目标标签ID
    
    Returns:
        JSON响应，包含转移的关联数量
    
    Example:
        POST /api/v1/tags/merge
        {"source_tag_id": 1, "target_tag_id": 2}
    """
    data = request.get_json()
    source_tag_id = data.get('source_tag_id')
    target_tag_id = data.get('target_tag_id')
    
    if not source_tag_id or not target_tag_id:
        return APIResponse.error('请提供源标签和目标标签ID', status_code=400)
    
    if source_tag_id == target_tag_id:
        return APIResponse.error('源标签和目标标签不能相同', status_code=400)
    
    tag_svc = ServiceLocator.get_tag_service()
    
    try:
        merge_data = TagMergeRequest(
            source_tag_id=source_tag_id,
            target_tag_id=target_tag_id
        )
        result = tag_svc.merge_tags(merge_data)
        
        cache = get_cache()
        cache.delete(CACHE_KEYS['tag_tree'])
        
        return APIResponse.success(data={
            'transferred_relations': result['transferred_relations'],
            'source_tag_id': source_tag_id,
            'target_tag_id': target_tag_id
        })
    except (TagNotFoundError, TagMergeError) as e:
        return APIResponse.error(str(e), status_code=400)
