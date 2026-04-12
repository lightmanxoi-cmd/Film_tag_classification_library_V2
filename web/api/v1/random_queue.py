"""
API v1 随机队列路由模块

提供随机队列相关的RESTful API接口。

路由列表：
    GET    /random-queue/status          # 获取队列状态
    POST   /random-queue/rx/videos       # 获取RX队列视频详情
    POST   /random-queue/rx/split-videos # 获取分割后的RX队列视频详情（多路同播）
    POST   /random-queue/refresh         # 强制刷新所有队列

功能特点：
    - 预计算随机序列，响应时间显著优于实时shuffle
    - RX队列按标签组合缓存，相同组合直接复用
    - 支持多路同播的序列分割
"""
from flask import Blueprint, request

from web.auth.decorators import login_required
from web.core.responses import APIResponse
from web.core.errors import handle_exceptions
from video_tag_system.utils.random_queue_manager import get_random_queue_manager

random_queue_bp = Blueprint('random_queue', __name__, url_prefix='/random-queue')


@random_queue_bp.route('/status', methods=['GET'])
@login_required
@handle_exceptions
def get_queue_status():
    """
    获取随机队列状态
    
    返回RA队列大小、RX队列数量、上次更新时间等信息。
    
    Returns:
        JSON响应，包含队列状态信息
    """
    manager = get_random_queue_manager()
    if manager is None:
        return APIResponse.error("随机队列管理器未初始化", status_code=503)
    
    status = manager.get_status()
    return APIResponse.success(data=status)


@random_queue_bp.route('/rx/videos', methods=['POST'])
@login_required
@handle_exceptions
def get_rx_videos():
    """
    获取RX队列视频详情
    
    根据标签组合获取或创建RX队列，返回对应的视频详情列表。
    如果该标签组合的RX队列已缓存，直接返回；否则从RA队列中筛选创建。
    
    Request Body:
        tags_by_category: 按分类组织的标签字典
            {"分类1": [tag_id1, tag_id2], "分类2": [tag_id3]}
    
    Returns:
        JSON响应，包含视频详情列表和队列信息
    
    Example:
        POST /api/v1/random-queue/rx/videos
        {
            "tags_by_category": {
                "类型": [1, 2],
                "地区": [5, 6]
            }
        }
    """
    manager = get_random_queue_manager()
    if manager is None:
        return APIResponse.error("随机队列管理器未初始化", status_code=503)
    
    data = request.get_json()
    tags_by_category = data.get('tags_by_category', {})
    
    if not tags_by_category:
        return APIResponse.success(data={
            'videos': [],
            'total': 0,
            'tag_key': 'empty'
        })
    
    from web.services import ServiceLocator
    session = ServiceLocator.get_db_session()
    
    try:
        videos = manager.get_rx_videos(tags_by_category, session)
        tag_key = manager._make_tag_key(tags_by_category)
        
        return APIResponse.success(data={
            'videos': videos,
            'total': len(videos),
            'tag_key': tag_key
        })
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


@random_queue_bp.route('/rx/split-videos', methods=['POST'])
@login_required
@handle_exceptions
def get_rx_split_videos():
    """
    获取分割后的RX队列视频详情（多路同播专用）
    
    根据标签组合获取RX队列，将其均匀分割为指定数量的子序列，
    每个子序列包含对应的视频详情。用于多路同播功能。
    
    Request Body:
        tags_by_category: 按分类组织的标签字典
        split_count: 分割数量，默认4（四路同播）
    
    Returns:
        JSON响应，包含分割后的视频详情组列表
    
    Example:
        POST /api/v1/random-queue/rx/split-videos
        {
            "tags_by_category": {
                "类型": [1, 2],
                "地区": [5, 6]
            },
            "split_count": 4
        }
    """
    manager = get_random_queue_manager()
    if manager is None:
        return APIResponse.error("随机队列管理器未初始化", status_code=503)
    
    data = request.get_json()
    tags_by_category = data.get('tags_by_category', {})
    split_count = data.get('split_count', 4)
    
    split_count = max(1, min(split_count, 8))
    
    if not tags_by_category:
        return APIResponse.success(data={
            'video_groups': [[] for _ in range(split_count)],
            'total': 0,
            'tag_key': 'empty'
        })
    
    from web.services import ServiceLocator
    session = ServiceLocator.get_db_session()
    
    try:
        video_groups, total = manager.get_rx_split_videos(
            tags_by_category, split_count, session
        )
        tag_key = manager._make_tag_key(tags_by_category)
        
        return APIResponse.success(data={
            'video_groups': video_groups,
            'total': total,
            'tag_key': tag_key
        })
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


@random_queue_bp.route('/refresh', methods=['POST'])
@login_required
@handle_exceptions
def refresh_queues():
    """
    强制刷新所有随机队列
    
    重新生成RA队列和所有RX队列。通常在添加/修改视频后手动调用。
    
    Returns:
        JSON响应，包含刷新结果信息
    """
    manager = get_random_queue_manager()
    if manager is None:
        return APIResponse.error("随机队列管理器未初始化", status_code=503)
    
    manager.refresh_all()
    
    status = manager.get_status()
    return APIResponse.success(data={
        'message': '随机队列已刷新',
        'ra_count': status['ra_count'],
        'rx_count': status['rx_count'],
        'last_update': status['last_update']
    })
