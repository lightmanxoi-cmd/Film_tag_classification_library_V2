"""
API v1 视频路由模块

提供视频相关的RESTful API接口。

路由列表：
    GET    /videos                    # 获取视频列表
    GET    /videos/<video_id>         # 获取视频详情
    POST   /videos/by-tags            # 按标签搜索视频
    POST   /videos/by-tags-advanced   # 高级标签搜索
    GET    /videos/stream/<video_id>  # 视频流播放
    GET    /videos/<video_id>/stream-url  # 获取视频流URL
    POST   /videos/<video_id>/gif     # 生成GIF预览

功能特点：
    - 支持分页查询
    - 支持随机排序
    - 支持关键词搜索
    - 支持多标签筛选
    - 支持Range请求的视频流
    - 自动缓存查询结果

使用示例：
    # 获取视频列表
    GET /api/v1/videos?page=1&page_size=50&search=关键词
    
    # 按标签搜索
    POST /api/v1/videos/by-tags
    {
        "tag_ids": [1, 2, 3],
        "match_all": false,
        "page": 1,
        "page_size": 50
    }
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
    """
    获取服务实例
    
    Returns:
        tuple: (video_service, tag_service, video_tag_service, db_session)
    """
    from web.services import get_services as _get_services
    return _get_services()


@videos_bp.route('', methods=['GET'])
@login_required
@handle_exceptions
def get_videos():
    """
    获取视频列表
    
    支持分页、搜索、随机排序。
    默认情况下（无筛选条件时）只显示"五星"标签的视频。
    
    Query Parameters:
        page: 页码，默认1
        page_size: 每页数量，默认50
        search: 搜索关键词
        random: 是否随机排序，默认true
        seed: 随机种子（用于保持随机顺序一致）
        all_videos: 是否显示全部视频（跳过默认五星筛选），默认false
    
    Returns:
        JSON响应，包含视频列表和分页信息
    
    Example:
        GET /api/v1/videos?page=1&page_size=20&search=测试&random=true
    """
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    search = request.args.get('search', None)
    random_order = request.args.get('random', 'true').lower() == 'true'
    random_seed = request.args.get('seed', None, type=int)
    show_all = request.args.get('all_videos', 'false').lower() == 'true'
    
    cache = get_cache()
    cache_key = f"videos:list:page:{page}:size:{page_size}:search:{search or ''}:random:{random_order}:seed:{random_seed or 0}:all:{show_all}"
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return APIResponse.success(data=cached_result, cached=True)
    
    video_svc, tag_svc, video_tag_svc, _ = get_services()
    
    if not search and not show_all:
        from video_tag_system.models.tag import Tag
        five_star_tag = tag_svc.get_tag_by_name('五星', parent_name='评级')
        if five_star_tag:
            result = video_svc.list_videos_by_tags(
                tag_ids=[five_star_tag.id],
                page=page,
                page_size=page_size,
                match_all=False,
                random_order=random_order,
                random_seed=random_seed
            )
        else:
            result = video_svc.list_videos(
                page=page,
                page_size=page_size,
                search=search,
                random_order=random_order,
                random_seed=random_seed
            )
    else:
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
    """
    获取视频详情
    
    Args:
        video_id: 视频ID
    
    Returns:
        JSON响应，包含视频详细信息
    
    Example:
        GET /api/v1/videos/1
    """
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
    """
    根据多个标签获取视频
    
    支持AND/OR逻辑筛选。
    
    Request Body:
        tag_ids: 标签ID列表
        page: 页码
        page_size: 每页数量
        match_all: 是否匹配所有标签（AND逻辑），false为OR逻辑
    
    Returns:
        JSON响应，包含视频列表和分页信息
    
    Example:
        POST /api/v1/videos/by-tags
        {
            "tag_ids": [1, 2, 3],
            "match_all": false,
            "page": 1,
            "page_size": 50
        }
    """
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
    """
    高级标签搜索
    
    支持按标签分类进行高级筛选，每个分类内的标签使用OR逻辑，
    不同分类之间使用AND逻辑。
    
    Request Body:
        tags_by_category: 按分类组织的标签字典
            {"分类1": [tag_id1, tag_id2], "分类2": [tag_id3]}
        page: 页码
        page_size: 每页数量
        random_order: 是否随机排序
        random_seed: 随机种子（用于保持随机顺序一致）
    
    Returns:
        JSON响应，包含视频列表和分页信息
    
    Example:
        POST /api/v1/videos/by-tags-advanced
        {
            "tags_by_category": {
                "类型": [1, 2],
                "地区": [5, 6]
            },
            "page": 1,
            "page_size": 50,
            "random_order": true,
            "random_seed": 12345
        }
    """
    data = request.get_json()
    tags_by_category = data.get('tags_by_category', {})
    page = data.get('page', 1)
    page_size = data.get('page_size', 50)
    random_order = data.get('random_order', False)
    random_seed = data.get('random_seed', None)
    
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
    cache_key = f"videos:advanced:{hash(category_str)}:page:{page}:size:{page_size}:random:{random_order}:seed:{random_seed or 0}"
    
    if not random_order:
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return APIResponse.success(data=cached_result, cached=True)
    
    video_svc, tag_svc, video_tag_svc, _ = get_services()
    
    result = video_svc.list_videos_by_tags_advanced(
        tags_by_category=tags_by_category,
        page=page,
        page_size=page_size,
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


from flask import current_app
import hashlib
import time
from functools import wraps
import threading

MIME_TYPES = {
    '.mp4': 'video/mp4',
    '.mkv': 'video/x-matroska',
    '.webm': 'video/webm',
    '.avi': 'video/x-msvideo',
    '.mov': 'video/quicktime',
    '.wmv': 'video/x-ms-wmv',
    '.flv': 'video/x-flv',
    '.m4v': 'video/mp4'
}

_active_streams = {}
_streams_lock = threading.Lock()


def _register_stream(video_id: int, client_ip: str) -> str:
    """注册视频流连接"""
    stream_id = f"{client_ip}:{video_id}:{time.time()}"
    with _streams_lock:
        if video_id not in _active_streams:
            _active_streams[video_id] = {}
        _active_streams[video_id][stream_id] = {
            'start_time': time.time(),
            'client_ip': client_ip,
            'bytes_sent': 0
        }
    return stream_id


def _unregister_stream(video_id: int, stream_id: str):
    """注销视频流连接"""
    with _streams_lock:
        if video_id in _active_streams and stream_id in _active_streams[video_id]:
            del _active_streams[video_id][stream_id]
            if not _active_streams[video_id]:
                del _active_streams[video_id]


def _update_stream_bytes(video_id: int, stream_id: str, bytes_sent: int):
    """更新流传输字节数"""
    with _streams_lock:
        if video_id in _active_streams and stream_id in _active_streams[video_id]:
            _active_streams[video_id][stream_id]['bytes_sent'] += bytes_sent


def get_active_streams_count(video_id: int = None) -> int:
    """获取活动流数量"""
    with _streams_lock:
        if video_id:
            return len(_active_streams.get(video_id, {}))
        return sum(len(streams) for streams in _active_streams.values())


def _get_stream_config():
    """获取视频流配置"""
    return {
        'chunk_size': current_app.config.get('VIDEO_STREAM_CHUNK_SIZE', 1024 * 1024),
        'cache_max_age': current_app.config.get('VIDEO_CACHE_MAX_AGE', 3600),
        'buffer_size': current_app.config.get('VIDEO_STREAM_BUFFER_SIZE', 64 * 1024),
        'log_enabled': current_app.config.get('VIDEO_STREAM_LOG_ENABLED', True),
        'max_bandwidth': current_app.config.get('VIDEO_STREAM_MAX_BANDWIDTH', 0)
    }


def _log_stream_request(video_id: int, file_path: str, range_header: str, 
                         status_code: int, bytes_sent: int, duration: float):
    """记录视频流请求日志"""
    config = _get_stream_config()
    if not config['log_enabled']:
        return
    
    from video_tag_system.utils.logger import get_logger
    logger = get_logger('video_stream')
    
    logger.info(
        f"视频流请求 | ID: {video_id} | 文件: {os.path.basename(file_path)} | "
        f"Range: {range_header or 'full'} | 状态: {status_code} | "
        f"字节: {bytes_sent} | 耗时: {duration:.3f}s"
    )


def _generate_file_etag(file_path: str, file_size: int, mtime: float) -> str:
    """生成文件ETag"""
    etag_base = f"{file_path}-{file_size}-{mtime}"
    return hashlib.md5(etag_base.encode()).hexdigest()


def _parse_range_header(range_header: str, file_size: int) -> tuple:
    """
    解析HTTP Range请求头
    
    支持多种Range格式:
    - bytes=0-499 (前500字节)
    - bytes=500- (从500字节到末尾)
    - bytes=-500 (最后500字节)
    
    Args:
        range_header: Range请求头值
        file_size: 文件总大小
    
    Returns:
        tuple: (start, end) 字节范围，无效时返回 (None, None)
    """
    try:
        range_match = re.match(r'bytes=(\d*)-(\d*)', range_header.strip())
        if not range_match:
            return None, None
        
        start_str, end_str = range_match.groups()
        
        if start_str and end_str:
            start = int(start_str)
            end = int(end_str)
        elif start_str:
            start = int(start_str)
            end = file_size - 1
        elif end_str:
            end = int(end_str)
            start = max(0, file_size - end)
            end = file_size - 1
        else:
            return None, None
        
        if start < 0 or end < start or start >= file_size:
            return None, None
        
        end = min(end, file_size - 1)
        return start, end
        
    except (ValueError, AttributeError):
        return None, None


def _generate_chunks(file_path: str, start: int, length: int, chunk_size: int, 
                     buffer_size: int = 65536, bandwidth_limit: int = 0,
                     video_id: int = None, stream_id: str = None):
    """
    生成文件块生成器
    
    使用缓冲读取优化IO性能，支持大文件流式传输。
    支持带宽限制防止服务器过载。
    
    Args:
        file_path: 文件路径
        start: 起始字节位置
        length: 读取长度
        chunk_size: 每次读取的块大小
        buffer_size: 文件缓冲区大小
        bandwidth_limit: 带宽限制 (bytes/s)，0表示无限制
        video_id: 视频ID（用于连接管理）
        stream_id: 流ID（用于连接管理）
    
    Yields:
        bytes: 文件数据块
    """
    try:
        with open(file_path, 'rb', buffering=buffer_size) as f:
            f.seek(start)
            remaining = length
            last_chunk_time = time.time()
            
            while remaining > 0:
                read_size = min(chunk_size, remaining)
                chunk = f.read(read_size)
                
                if not chunk:
                    break
                
                remaining -= len(chunk)
                
                if bandwidth_limit > 0:
                    chunk_size_bytes = len(chunk)
                    expected_time = chunk_size_bytes / bandwidth_limit
                    elapsed = time.time() - last_chunk_time
                    
                    if elapsed < expected_time:
                        time.sleep(expected_time - elapsed)
                    
                    last_chunk_time = time.time()
                
                if video_id and stream_id:
                    _update_stream_bytes(video_id, stream_id, len(chunk))
                
                yield chunk
    finally:
        if video_id and stream_id:
            _unregister_stream(video_id, stream_id)


@videos_bp.route('/stream/<int:video_id>')
@login_required
@handle_exceptions
def serve_video_by_id(video_id):
    """
    视频流播放
    
    支持HTTP Range请求，实现视频拖动播放。
    添加缓存头优化重复播放性能。
    
    Args:
        video_id: 视频ID
    
    Returns:
        Response: 视频流响应
    
    Features:
        - 支持Range请求（206 Partial Content）
        - ETag支持（避免重复传输）
        - 条件请求（If-None-Match, If-Range）
        - 流式传输（避免内存溢出）
        - 浏览器缓存优化
        - 自动识别视频MIME类型
        - 请求日志记录
    """
    start_time = time.time()
    config = _get_stream_config()
    
    video_svc, _, _, _ = get_services()
    video = video_svc.get_video(video_id)
    full_path = video.file_path
    
    if not os.path.exists(full_path):
        _log_stream_request(video_id, full_path, None, 404, 0, time.time() - start_time)
        return APIResponse.not_found(f"视频不存在: {full_path}")
    
    file_size = os.path.getsize(full_path)
    file_mtime = os.path.getmtime(full_path)
    file_ext = os.path.splitext(full_path)[1].lower()
    mimetype = MIME_TYPES.get(file_ext, 'video/mp4')
    
    etag = _generate_file_etag(full_path, file_size, file_mtime)
    
    if_none_match = request.headers.get('If-None-Match')
    if if_none_match and if_none_match == etag:
        return Response(status=304)
    
    range_header = request.headers.get('Range')
    if_range = request.headers.get('If-Range')
    
    use_range = range_header is not None
    if if_range and if_range != etag:
        try:
            if_range_time = time.mktime(time.strptime(if_range, '%a, %d %b %Y %H:%M:%S GMT'))
            if file_mtime > if_range_time:
                use_range = False
        except (ValueError, TypeError):
            pass
    
    if use_range and range_header:
        start, end = _parse_range_header(range_header, file_size)
        
        if start is None:
            response = Response(status=416)
            response.headers['Content-Range'] = f'bytes */{file_size}'
            _log_stream_request(video_id, full_path, range_header, 416, 0, time.time() - start_time)
            return response
        
        length = end - start + 1
        client_ip = request.remote_addr or 'unknown'
        stream_id = _register_stream(video_id, client_ip)
        
        response = Response(
            _generate_chunks(
                full_path, start, length, 
                config['chunk_size'], 
                config['buffer_size'],
                config['max_bandwidth'],
                video_id, 
                stream_id
            ),
            206,
            mimetype=mimetype,
            direct_passthrough=True
        )
        response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
        response.headers['Content-Length'] = str(length)
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['ETag'] = etag
        response.headers['Cache-Control'] = f'public, max-age={config["cache_max_age"]}'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Last-Modified'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(file_mtime))
        response.headers['X-Stream-Id'] = stream_id
        
        _log_stream_request(video_id, full_path, range_header, 206, length, time.time() - start_time)
        return response
    
    response = send_file(
        full_path,
        mimetype=mimetype,
        conditional=True,
        etag=False,
        last_modified=file_mtime
    )
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['ETag'] = etag
    response.headers['Cache-Control'] = f'public, max-age={config["cache_max_age"]}'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Last-Modified'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(file_mtime))
    
    _log_stream_request(video_id, full_path, None, 200, file_size, time.time() - start_time)
    return response


@videos_bp.route('/<int:video_id>/stream-url', methods=['GET'])
@login_required
@handle_exceptions
def get_video_stream_url(video_id):
    """
    获取视频流URL
    
    返回视频的流媒体播放地址。
    
    Args:
        video_id: 视频ID
    
    Returns:
        JSON响应，包含流媒体URL和视频信息
    
    Example:
        GET /api/v1/videos/1/stream-url
        {
            "success": true,
            "data": {
                "stream_url": "/api/v1/videos/stream/1",
                "title": "视频标题",
                "duration": 3600,
                "file_ext": ".mp4"
            }
        }
    """
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
    """
    为视频生成GIF预览
    
    使用FFmpeg从视频中间位置截取片段生成GIF动画。
    
    Args:
        video_id: 视频ID
    
    Returns:
        JSON响应，包含GIF URL
    
    Example:
        POST /api/v1/videos/1/gif
        {
            "success": true,
            "message": "GIF生成成功",
            "data": {
                "gif_url": "/static/gifs/视频标题.gif"
            }
        }
    """
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


@videos_bp.route('/batch/thumbnails', methods=['POST'])
@login_required
@handle_exceptions
def batch_generate_thumbnails():
    """
    批量异步生成缩略图
    
    将缩略图生成任务提交到后台执行，立即返回任务ID。
    通过任务ID可以查询进度和结果。
    
    Request Body:
        video_ids: 视频ID列表（可选，不提供则处理所有缺少缩略图的视频）
        force: 是否强制重新生成，默认False
    
    Returns:
        JSON响应，包含任务ID
    
    Example:
        POST /api/v1/videos/batch/thumbnails
        {
            "video_ids": [1, 2, 3],
            "force": false
        }
        
        Response:
        {
            "success": true,
            "message": "任务已提交",
            "data": {
                "task_id": "abc123",
                "total": 3
            }
        }
    """
    from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator
    
    data = request.get_json() or {}
    video_ids = data.get('video_ids', None)
    force = data.get('force', False)
    
    video_svc, _, _, _ = get_services()
    thumbnail_gen = get_thumbnail_generator()
    
    if video_ids:
        videos_to_process = []
        for vid in video_ids:
            try:
                video = video_svc.get_video(vid)
                video_title = video.title or os.path.basename(video.file_path)
                videos_to_process.append((vid, video.file_path, video_title))
            except Exception:
                continue
    else:
        result = video_svc.list_videos(page=1, page_size=10000)
        videos_to_process = [
            (v.id, v.file_path, v.title or os.path.basename(v.file_path))
            for v in result.items
            if force or not thumbnail_gen.has_thumbnail(v.title or os.path.basename(v.file_path))
        ]
    
    if not videos_to_process:
        return APIResponse.success(message='没有需要处理的视频', data={'task_id': None, 'total': 0})
    
    task_id = thumbnail_gen.submit_thumbnail_task(
        videos=videos_to_process,
        force=force,
        task_name=f"批量生成缩略图 ({len(videos_to_process)}个视频)"
    )
    
    return APIResponse.success(
        message='任务已提交',
        data={
            'task_id': task_id,
            'total': len(videos_to_process)
        }
    )


@videos_bp.route('/batch/gifs', methods=['POST'])
@login_required
@handle_exceptions
def batch_generate_gifs():
    """
    批量异步生成GIF预览
    
    将GIF生成任务提交到后台执行，立即返回任务ID。
    GIF生成比缩略图更耗时，建议使用异步方式。
    
    Request Body:
        video_ids: 视频ID列表（可选，不提供则处理所有缺少GIF的视频）
        force: 是否强制重新生成，默认False
    
    Returns:
        JSON响应，包含任务ID
    
    Example:
        POST /api/v1/videos/batch/gifs
        {
            "video_ids": [1, 2, 3],
            "force": false
        }
        
        Response:
        {
            "success": true,
            "message": "任务已提交",
            "data": {
                "task_id": "abc123",
                "total": 3
            }
        }
    """
    from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator
    
    data = request.get_json() or {}
    video_ids = data.get('video_ids', None)
    force = data.get('force', False)
    
    video_svc, _, _, _ = get_services()
    thumbnail_gen = get_thumbnail_generator()
    
    if video_ids:
        videos_to_process = []
        for vid in video_ids:
            try:
                video = video_svc.get_video(vid)
                video_title = video.title or os.path.basename(video.file_path)
                videos_to_process.append((vid, video.file_path, video_title, video.duration))
            except Exception:
                continue
    else:
        result = video_svc.list_videos(page=1, page_size=10000)
        videos_to_process = [
            (v.id, v.file_path, v.title or os.path.basename(v.file_path), v.duration)
            for v in result.items
            if force or not thumbnail_gen.has_gif(v.title or os.path.basename(v.file_path))
        ]
    
    if not videos_to_process:
        return APIResponse.success(message='没有需要处理的视频', data={'task_id': None, 'total': 0})
    
    task_id = thumbnail_gen.submit_gif_task(
        videos=videos_to_process,
        force=force,
        task_name=f"批量生成GIF预览 ({len(videos_to_process)}个视频)"
    )
    
    return APIResponse.success(
        message='任务已提交',
        data={
            'task_id': task_id,
            'total': len(videos_to_process)
        }
    )


@videos_bp.route('/missing-thumbnails', methods=['GET'])
@login_required
@handle_exceptions
def get_missing_thumbnails():
    """
    获取缺少缩略图的视频列表
    
    Query Parameters:
        page: 页码，默认1
        page_size: 每页数量，默认50
    
    Returns:
        JSON响应，包含缺少缩略图的视频列表
    
    Example:
        GET /api/v1/videos/missing-thumbnails?page=1&page_size=20
    """
    from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator
    
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    
    video_svc, _, _, _ = get_services()
    thumbnail_gen = get_thumbnail_generator()
    
    result = video_svc.list_videos(page=page, page_size=page_size)
    
    missing_videos = []
    for v in result.items:
        video_title = v.title or os.path.basename(v.file_path)
        if not thumbnail_gen.has_thumbnail(video_title):
            missing_videos.append({
                'id': v.id,
                'title': video_title,
                'file_path': v.file_path,
                'duration': v.duration
            })
    
    return APIResponse.success(data={
        'videos': missing_videos,
        'total': len(missing_videos),
        'page': page,
        'page_size': page_size
    })


@videos_bp.route('/streams/active', methods=['GET'])
@login_required
@handle_exceptions
def get_active_streams():
    """
    获取当前活动的视频流连接
    
    用于监控服务器负载和流媒体状态。
    
    Returns:
        JSON响应，包含活动流列表和统计信息
    
    Example:
        GET /api/v1/videos/streams/active
        {
            "success": true,
            "data": {
                "total_streams": 3,
                "streams_by_video": {
                    "1": [{"client_ip": "127.0.0.1", "start_time": 1234567890, "bytes_sent": 1048576}]
                }
            }
        }
    """
    with _streams_lock:
        streams_data = {}
        total_bytes = 0
        
        for vid, streams in _active_streams.items():
            streams_data[vid] = []
            for stream_id, info in streams.items():
                streams_data[vid].append({
                    'stream_id': stream_id,
                    'client_ip': info['client_ip'],
                    'start_time': info['start_time'],
                    'duration': time.time() - info['start_time'],
                    'bytes_sent': info['bytes_sent']
                })
                total_bytes += info['bytes_sent']
    
    return APIResponse.success(data={
        'total_streams': get_active_streams_count(),
        'total_bytes_sent': total_bytes,
        'streams_by_video': streams_data
    })


@videos_bp.route('/missing-gifs', methods=['GET'])
@login_required
@handle_exceptions
def get_missing_gifs():
    """
    获取缺少GIF预览的视频列表
    
    Query Parameters:
        page: 页码，默认1
        page_size: 每页数量，默认50
    
    Returns:
        JSON响应，包含缺少GIF的视频列表
    
    Example:
        GET /api/v1/videos/missing-gifs?page=1&page_size=20
    """
    from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator
    
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    
    video_svc, _, _, _ = get_services()
    thumbnail_gen = get_thumbnail_generator()
    
    result = video_svc.list_videos(page=page, page_size=page_size)
    
    missing_videos = []
    for v in result.items:
        video_title = v.title or os.path.basename(v.file_path)
        if not thumbnail_gen.has_gif(video_title):
            missing_videos.append({
                'id': v.id,
                'title': video_title,
                'file_path': v.file_path,
                'duration': v.duration
            })
    
    return APIResponse.success(data={
        'videos': missing_videos,
        'total': len(missing_videos),
        'page': page,
        'page_size': page_size
    })
