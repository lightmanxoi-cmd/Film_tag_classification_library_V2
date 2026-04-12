"""
API v1 视频导入路由模块

提供视频导入相关的RESTful API接口。

路由列表：
    POST   /import/scan-folder     # 扫描文件夹中的视频文件
    POST   /import/video           # 导入单个视频并添加标签
    GET    /import/check-video     # 检查视频是否已存在

功能特点：
    - 支持扫描本地文件夹
    - 支持多级标签关联
    - 支持视频重复检测
    - 支持更新已存在的视频

使用示例：
    # 扫描文件夹
    POST /api/v1/import/scan-folder
    {
        "folder_path": "C:\\Videos",
        "recursive": false
    }
    
    # 导入视频
    POST /api/v1/import/video
    {
        "file_path": "C:\\Videos\\movie.mp4",
        "tag_ids": [1, 2, 3]
    }
"""
import os
from flask import Blueprint, request, g

from web.auth.decorators import login_required
from web.core.responses import APIResponse
from web.core.errors import handle_exceptions
from web.services import ServiceLocator

import_bp = Blueprint('import', __name__, url_prefix='/import')


VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv'}


def _is_video_file(filename: str) -> bool:
    """
    判断文件是否为视频文件
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 是视频文件返回True，否则返回False
    """
    ext = os.path.splitext(filename)[1].lower()
    return ext in VIDEO_EXTENSIONS


@import_bp.route('/scan-folder', methods=['POST'])
@login_required
@handle_exceptions
def scan_folder():
    """
    扫描文件夹中的视频文件
    
    扫描指定文件夹中的所有视频文件，返回文件列表。
    
    Request Body:
        folder_path: 文件夹路径
        recursive: 是否递归扫描子文件夹（可选，默认false）
    
    Returns:
        JSON响应，包含视频文件列表
    
    Example:
        POST /api/v1/import/scan-folder
        {
            "folder_path": "C:\\Videos",
            "recursive": false
        }
    """
    data = request.get_json()
    folder_path = data.get('folder_path', '')
    recursive = data.get('recursive', False)
    
    if not folder_path:
        return APIResponse.error('文件夹路径不能为空', status_code=400)
    
    folder_path = folder_path.strip()
    if len(folder_path) >= 2:
        if (folder_path[0] == '"' and folder_path[-1] == '"') or \
           (folder_path[0] == "'" and folder_path[-1] == "'"):
            folder_path = folder_path[1:-1].strip()
    
    if not os.path.isdir(folder_path):
        return APIResponse.error(f'文件夹不存在: {folder_path}', status_code=400)
    
    video_files = []
    
    if recursive:
        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                if _is_video_file(filename):
                    video_files.append({
                        'name': filename,
                        'path': os.path.join(root, filename),
                        'title': os.path.splitext(filename)[0]
                    })
    else:
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if os.path.isfile(filepath) and _is_video_file(filename):
                video_files.append({
                    'name': filename,
                    'path': filepath,
                    'title': os.path.splitext(filename)[0]
                })
    
    video_files.sort(key=lambda x: x['name'].lower())
    
    return APIResponse.success(data={
        'folder_path': folder_path,
        'video_count': len(video_files),
        'videos': video_files
    })


@import_bp.route('/check-video', methods=['GET'])
@login_required
@handle_exceptions
def check_video_exists():
    """
    检查视频是否已存在
    
    根据文件路径或标题检查视频是否已在数据库中。
    
    Query Parameters:
        file_path: 视频文件路径（可选）
        title: 视频标题（可选）
    
    Returns:
        JSON响应，包含视频是否存在及视频信息
    
    Example:
        GET /api/v1/import/check-video?file_path=C:\\Videos\\movie.mp4
    """
    file_path = request.args.get('file_path', '')
    title = request.args.get('title', '')
    
    if not file_path and not title:
        return APIResponse.error('请提供文件路径或标题', status_code=400)
    
    video_svc = ServiceLocator.get_video_service()
    
    existing_video = None
    
    if file_path:
        try:
            existing_video = video_svc.get_video_by_path(file_path)
        except Exception:
            pass
    
    if not existing_video and title:
        from sqlalchemy import select
        from video_tag_system.models.video import Video
        from video_tag_system.core.database import get_db_manager
        
        db = get_db_manager()
        with db.get_session() as session:
            stmt = select(Video).where(Video.title == title)
            video = session.execute(stmt).scalar_one_or_none()
            if video:
                existing_video = video_svc.get_video(video.id)
    
    if existing_video:
        return APIResponse.success(data={
            'exists': True,
            'video': {
                'id': existing_video.id,
                'title': existing_video.title,
                'file_path': existing_video.file_path,
                'tags': [{'id': t.id, 'name': t.name, 'parent_id': t.parent_id} for t in existing_video.tags]
            }
        })
    
    return APIResponse.success(data={
        'exists': False,
        'video': None
    })


@import_bp.route('/video', methods=['POST'])
@login_required
@handle_exceptions
def import_video():
    """
    导入视频并添加标签
    
    根据标题判断视频是否已存在：
    - 如果存在：更新路径并添加新标签
    - 如果不存在：创建新视频记录并添加标签
    
    Request Body:
        file_path: 视频文件路径（可选，如果提供会验证文件是否存在）
        title: 视频标题（可选，如果不提供则从file_path提取）
        tag_ids: 标签ID列表（二级标签ID，程序会自动关联对应的一级标签）
    
    Returns:
        JSON响应，包含导入结果
    
    Example:
        POST /api/v1/import/video
        {
            "file_path": "C:\\Videos\\movie.mp4",
            "tag_ids": [2, 5]
        }
        
        或仅使用标题：
        {
            "title": "movie",
            "tag_ids": [2, 5]
        }
    """
    data = request.get_json()
    file_path = data.get('file_path', '')
    title = data.get('title', '')
    tag_ids = data.get('tag_ids', [])
    
    if not file_path and not title:
        return APIResponse.error('请提供文件路径或标题', status_code=400)
    
    if file_path:
        file_path = file_path.strip()
        if len(file_path) >= 2:
            if (file_path[0] == '"' and file_path[-1] == '"') or \
               (file_path[0] == "'" and file_path[-1] == "'"):
                file_path = file_path[1:-1].strip()
    
    if not title and file_path:
        filename = os.path.basename(file_path)
        title = os.path.splitext(filename)[0]
    
    if not title:
        return APIResponse.error('无法确定视频标题', status_code=400)
    
    video_svc = ServiceLocator.get_video_service()
    tag_svc = ServiceLocator.get_tag_service()
    video_tag_svc = ServiceLocator.get_video_tag_service()
    
    all_tag_ids = set()
    
    for tag_id in tag_ids:
        try:
            tag = tag_svc.get_tag(tag_id)
            all_tag_ids.add(tag_id)
            if tag.parent_id:
                all_tag_ids.add(tag.parent_id)
        except Exception as e:
            return APIResponse.error(f'标签ID {tag_id} 不存在', status_code=400)
    
    from sqlalchemy import select
    from video_tag_system.models.video import Video
    from video_tag_system.core.database import get_db_manager
    
    db = get_db_manager()
    
    with db.get_session() as session:
        stmt = select(Video).where(Video.title == title)
        existing_video = session.execute(stmt).scalar_one_or_none()
        
        if existing_video:
            if file_path and os.path.exists(file_path):
                from video_tag_system.models.video import VideoUpdate
                update_data = VideoUpdate(title=title, file_path=file_path)
                video_svc.update_video(existing_video.id, update_data)
            
            existing_tags = video_tag_svc.get_video_tags(existing_video.id)
            existing_tag_ids = {tag.id for tag in existing_tags}
            
            tags_added = 0
            for tag_id in all_tag_ids:
                if tag_id not in existing_tag_ids:
                    video_tag_svc.add_tag_to_video(existing_video.id, tag_id)
                    tags_added += 1
            
            updated_tags = video_tag_svc.get_video_tags(existing_video.id)
            
            return APIResponse.success(data={
                'action': 'updated',
                'video': {
                    'id': existing_video.id,
                    'title': title,
                    'file_path': file_path or existing_video.file_path,
                    'tags_added': tags_added,
                    'total_tags': len(updated_tags),
                    'tags': [{'id': t.id, 'name': t.name, 'parent_id': t.parent_id} for t in updated_tags]
                },
                'message': f'视频已更新，新增 {tags_added} 个标签'
            })
        
        else:
            from video_tag_system.models.video import VideoCreate
            
            actual_file_path = file_path if (file_path and os.path.exists(file_path)) else ''
            
            video_data = VideoCreate(file_path=actual_file_path, title=title)
            video = video_svc.create_video(video_data)
            
            for tag_id in all_tag_ids:
                video_tag_svc.add_tag_to_video(video.id, tag_id)
            
            try:
                video_svc.refresh_video_media_url(video.id)
            except Exception:
                pass
            
            return APIResponse.success(data={
                'action': 'created',
                'video': {
                    'id': video.id,
                    'title': title,
                    'file_path': actual_file_path,
                    'total_tags': len(all_tag_ids),
                    'tags': [{'id': t.id, 'name': t.name, 'parent_id': t.parent_id} for t in video.tags]
                },
                'message': '视频导入成功'
            })


@import_bp.route('/batch', methods=['POST'])
@login_required
@handle_exceptions
def batch_import_videos():
    """
    批量导入视频
    
    批量导入多个视频并添加标签。
    
    Request Body:
        videos: 视频列表，每个元素包含 file_path 和 tag_ids
        stop_on_error: 遇到错误是否停止（可选，默认false）
    
    Returns:
        JSON响应，包含批量导入结果
    
    Example:
        POST /api/v1/import/batch
        {
            "videos": [
                {"file_path": "C:\\Videos\\movie1.mp4", "tag_ids": [1, 2]},
                {"file_path": "C:\\Videos\\movie2.mp4", "tag_ids": [3, 4]}
            ],
            "stop_on_error": false
        }
    """
    data = request.get_json()
    videos = data.get('videos', [])
    stop_on_error = data.get('stop_on_error', False)
    
    if not videos:
        return APIResponse.error('视频列表不能为空', status_code=400)
    
    results = {
        'success': [],
        'failed': [],
        'total': len(videos)
    }
    
    for video_data in videos:
        file_path = video_data.get('file_path', '')
        tag_ids = video_data.get('tag_ids', [])
        
        try:
            if not file_path:
                raise ValueError('文件路径不能为空')
            
            if not os.path.exists(file_path):
                raise ValueError(f'文件不存在: {file_path}')
            
            video_svc = ServiceLocator.get_video_service()
            tag_svc = ServiceLocator.get_tag_service()
            video_tag_svc = ServiceLocator.get_video_tag_service()
            
            filename = os.path.basename(file_path)
            title = os.path.splitext(filename)[0]
            
            all_tag_ids = set()
            for tag_id in tag_ids:
                try:
                    tag = tag_svc.get_tag(tag_id)
                    all_tag_ids.add(tag_id)
                    if tag.parent_id:
                        all_tag_ids.add(tag.parent_id)
                except Exception:
                    pass
            
            from sqlalchemy import select
            from video_tag_system.models.video import Video
            from video_tag_system.core.database import get_db_manager
            
            db = get_db_manager()
            
            with db.get_session() as session:
                stmt = select(Video).where(Video.title == title)
                existing_video = session.execute(stmt).scalar_one_or_none()
                
                if existing_video:
                    from video_tag_system.models.video import VideoUpdate
                    update_data = VideoUpdate(title=title, file_path=file_path)
                    video_svc.update_video(existing_video.id, update_data)
                    
                    existing_tags = video_tag_svc.get_video_tags(existing_video.id)
                    existing_tag_ids = {tag.id for tag in existing_tags}
                    
                    tags_added = 0
                    for tag_id in all_tag_ids:
                        if tag_id not in existing_tag_ids:
                            video_tag_svc.add_tag_to_video(existing_video.id, tag_id)
                            tags_added += 1
                    
                    results['success'].append({
                        'file_path': file_path,
                        'title': title,
                        'action': 'updated',
                        'tags_added': tags_added
                    })
                else:
                    from video_tag_system.models.video import VideoCreate
                    video_data_create = VideoCreate(file_path=file_path, title=title)
                    video = video_svc.create_video(video_data_create)
                    
                    for tag_id in all_tag_ids:
                        video_tag_svc.add_tag_to_video(video.id, tag_id)
                    
                    results['success'].append({
                        'file_path': file_path,
                        'title': title,
                        'action': 'created',
                        'video_id': video.id
                    })
        
        except Exception as e:
            results['failed'].append({
                'file_path': file_path,
                'error': str(e)
            })
            
            if stop_on_error:
                break
    
    return APIResponse.success(data=results)
