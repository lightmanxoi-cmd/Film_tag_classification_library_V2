"""
API v1 视频路由
"""
import os
import re
from flask import Blueprint, request, send_file, Response

from web.auth.decorators import login_required
from web.core.responses import APIResponse
from web.core.errors import handle_exceptions
from video_tag_system.utils.cache import get_cache, CACHE_KEYS

videos_bp = Blueprint('videos', __name__, url_prefix='/videos')


def get_services():
    """获取服务实例"""
    from web.services import get_services as _get_services
    return _get_services()


@videos_bp.route('', methods=['GET'])
@login_required
@handle_exceptions
def get_videos():
    """获取视频列表"""
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    search = request.args.get('search', None)
    random_order = request.args.get('random', 'true').lower() == 'true'
    random_seed = request.args.get('seed', None, type=int)
    
    cache = get_cache()
    cache_key = f"videos:list:page:{page}:size:{page_size}:search:{search or ''}:random:{random_order}:seed:{random_seed or 0}"
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return APIResponse.success(data=cached_result, cached=True)
    
    video_svc, tag_svc, video_tag_svc, _ = get_services()
    
    result = video_svc.list_videos(
        page=page,
        page_size=page_size,
        search=search,
        random_order=random_order,
        random_seed=random_seed
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


@videos_bp.route('/<int:video_id>', methods=['GET'])
@login_required
@handle_exceptions
def get_video_detail(video_id):
    """获取视频详情"""
    cache = get_cache()
    cache_key = f"{CACHE_KEYS['video_by_id']}:{video_id}"
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return APIResponse.success(data=cached_result, cached=True)
    
    video_svc, _, _, _ = get_services()
    
    video = video_svc.get_video(video_id)
    response_data = {
        'id': video.id,
        'title': video.title or os.path.basename(video.file_path),
        'file_path': video.file_path,
        'duration': video.duration,
        'description': video.description,
        'tags': [{'id': t.id, 'name': t.name, 'parent_id': t.parent_id} for t in video.tags]
    }
    
    cache.set(cache_key, response_data, ttl=120)
    return APIResponse.success(data=response_data, cached=False)


@videos_bp.route('/by-tags', methods=['POST'])
@login_required
@handle_exceptions
def get_videos_by_multiple_tags():
    """根据多个标签获取视频"""
    data = request.get_json()
    tag_ids = data.get('tag_ids', [])
    page = data.get('page', 1)
    page_size = data.get('page_size', 50)
    match_all = data.get('match_all', False)
    
    if not tag_ids:
        return APIResponse.success(data={
            'videos': [],
            'total': 0,
            'page': page,
            'page_size': page_size,
            'total_pages': 0
        })
    
    cache = get_cache()
    tag_ids_str = ','.join(map(str, sorted(tag_ids)))
    cache_key = f"videos:by_tags:{tag_ids_str}:page:{page}:size:{page_size}:all:{match_all}"
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return APIResponse.success(data=cached_result, cached=True)
    
    video_svc, tag_svc, video_tag_svc, _ = get_services()
    
    result = video_svc.list_videos_by_tags(
        tag_ids=tag_ids,
        page=page,
        page_size=page_size,
        match_all=match_all
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


@videos_bp.route('/by-tags-advanced', methods=['POST'])
@login_required
@handle_exceptions
def get_videos_by_tags_advanced():
    """高级标签搜索"""
    data = request.get_json()
    tags_by_category = data.get('tags_by_category', {})
    page = data.get('page', 1)
    page_size = data.get('page_size', 50)
    
    if not tags_by_category:
        return APIResponse.success(data={
            'videos': [],
            'total': 0,
            'page': page,
            'page_size': page_size,
            'total_pages': 0
        })
    
    cache = get_cache()
    category_str = str(sorted([(k, sorted(v)) for k, v in tags_by_category.items()]))
    cache_key = f"videos:advanced:{hash(category_str)}:page:{page}:size:{page_size}"
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return APIResponse.success(data=cached_result, cached=True)
    
    video_svc, tag_svc, video_tag_svc, _ = get_services()
    
    result = video_svc.list_videos_by_tags_advanced(
        tags_by_category=tags_by_category,
        page=page,
        page_size=page_size
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


VIDEO_STREAM_CHUNK_SIZE = 1024 * 1024
VIDEO_CACHE_MAX_AGE = 3600


def _parse_range_header(range_header: str, file_size: int) -> tuple:
    start = 0
    end = file_size - 1
    
    match = re.search(r'bytes=(\d+)-(\d*)', range_header)
    if match:
        start = int(match.group(1))
        if match.group(2):
            end = int(match.group(2))
        end = min(end, file_size - 1)
    
    if start > end or start >= file_size:
        return None, None
    
    return start, end


def _generate_chunks(file_path: str, start: int, length: int, chunk_size: int):
    with open(file_path, 'rb') as f:
        f.seek(start)
        remaining = length
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            chunk = f.read(read_size)
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@videos_bp.route('/stream/<int:video_id>')
@login_required
@handle_exceptions
def serve_video_by_id(video_id):
    video_svc, _, _, _ = get_services()
    video = video_svc.get_video(video_id)
    full_path = video.file_path
    
    if not os.path.exists(full_path):
        return APIResponse.not_found(f"视频不存在: {full_path}")
    
    file_size = os.path.getsize(full_path)
    file_ext = os.path.splitext(full_path)[1].lower()
    
    mime_types = {
        '.mp4': 'video/mp4',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
        '.avi': 'video/x-msvideo',
        '.mov': 'video/quicktime'
    }
    mimetype = mime_types.get(file_ext, 'video/mp4')
    
    range_header = request.headers.get('Range', None)
    
    if range_header:
        start, end = _parse_range_header(range_header, file_size)
        
        if start is None:
            response = Response(status=416)
            response.headers.add('Content-Range', f'bytes */{file_size}')
            return response
        
        length = end - start + 1
        
        response = Response(
            _generate_chunks(full_path, start, length, VIDEO_STREAM_CHUNK_SIZE),
            206,
            mimetype=mimetype,
            direct_passthrough=True
        )
        response.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
        response.headers.add('Accept-Ranges', 'bytes')
        response.headers.add('Content-Length', str(length))
        response.headers.add('Cache-Control', f'public, max-age={VIDEO_CACHE_MAX_AGE}')
        response.headers.add('X-Content-Type-Options', 'nosniff')
        return response
    
    response = send_file(full_path, mimetype=mimetype)
    response.headers.add('Accept-Ranges', 'bytes')
    response.headers.add('Cache-Control', f'public, max-age={VIDEO_CACHE_MAX_AGE}')
    response.headers.add('X-Content-Type-Options', 'nosniff')
    return response


@videos_bp.route('/<int:video_id>/stream-url', methods=['GET'])
@login_required
@handle_exceptions
def get_video_stream_url(video_id):
    """获取视频流URL"""
    video_svc, _, _, _ = get_services()
    video = video_svc.get_video(video_id)
    file_path = video.file_path
    file_ext = os.path.splitext(file_path)[1].lower()
    
    stream_url = f'/api/v1/videos/stream/{video_id}'
    
    return APIResponse.success(data={
        'stream_url': stream_url,
        'title': video.title or os.path.basename(file_path),
        'duration': video.duration,
        'file_ext': file_ext
    })


@videos_bp.route('/<int:video_id>/gif', methods=['POST'])
@login_required
@handle_exceptions
def generate_gif_for_video(video_id):
    """为视频生成GIF"""
    video_svc, _, _, _ = get_services()
    video = video_svc.get_video(video_id)
    video_title = video.title or os.path.basename(video.file_path)
    
    from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator
    thumbnail_gen = get_thumbnail_generator()
    
    if thumbnail_gen.has_gif(video_title):
        return APIResponse.success(
            message='GIF已存在',
            data={'gif_url': thumbnail_gen.get_gif_url(video_title)}
        )
    
    result = thumbnail_gen.generate_gif(video.file_path, video_title, video.duration)
    
    if result:
        return APIResponse.success(
            message='GIF生成成功',
            data={'gif_url': thumbnail_gen.get_gif_url(video_title)}
        )
    else:
        return APIResponse.error('GIF生成失败')
