"""
奈飞风格视频播放网站 - Flask后端
"""
import os
import re
from flask import Flask, jsonify, request, send_file, render_template, Response
from flask_cors import CORS
from video_tag_system.core.database import DatabaseManager
from video_tag_system.services.video_service import VideoService
from video_tag_system.services.tag_service import TagService
from video_tag_system.services.video_tag_service import VideoTagService
from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator
from sqlalchemy import text

app = Flask(__name__, 
            static_folder='web/static',
            template_folder='web/templates')
CORS(app)

db_manager = DatabaseManager(database_url="sqlite:///./video_library.db", echo=False)
db_manager.create_tables()

VIDEO_BASE_PATH = "F:\\666"

def get_services():
    session = db_manager.session_factory()
    return (
        VideoService(session),
        TagService(session),
        VideoTagService(session),
        session
    )

def update_thumbnails():
    """启动时更新所有视频缩略图"""
    print("=" * 50)
    print("开始检查视频缩略图...")
    
    thumbnail_gen = get_thumbnail_generator()
    session = db_manager.session_factory()
    
    try:
        result = session.execute(text("SELECT id, file_path FROM videos")).fetchall()
        videos = [(row[0], row[1]) for row in result]
        
        print(f"共有 {len(videos)} 个视频")
        
        results = thumbnail_gen.batch_generate(videos, max_workers=2, force=False)
        
        print(f"缩略图生成完成: 成功 {results['success']}, 失败 {results['failed']}, 跳过 {results['skipped']}")
    except Exception as e:
        print(f"更新缩略图时出错: {e}")
    finally:
        session.close()
    
    print("=" * 50)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/tags/tree', methods=['GET'])
def get_tag_tree():
    video_svc, tag_svc, video_tag_svc, session = get_services()
    try:
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
        return jsonify({'success': True, 'data': result})
    finally:
        session.close()

@app.route('/api/tags/<int:tag_id>/videos', methods=['GET'])
def get_videos_by_tag(tag_id):
    video_svc, tag_svc, video_tag_svc, session = get_services()
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        
        result = video_svc.list_videos_by_tags(
            tag_ids=[tag_id],
            page=page,
            page_size=page_size,
            match_all=False
        )
        
        thumbnail_gen = get_thumbnail_generator()
        
        videos = []
        for v in result.items:
            videos.append({
                'id': v.id,
                'title': v.title or os.path.basename(v.file_path),
                'file_path': v.file_path,
                'duration': v.duration,
                'tags': [{'id': t.id, 'name': t.name, 'parent_id': t.parent_id} for t in v.tags],
                'thumbnail': thumbnail_gen.get_thumbnail_url(v.id)
            })
        
        return jsonify({
            'success': True,
            'data': {
                'videos': videos,
                'total': result.total,
                'page': result.page,
                'page_size': result.page_size,
                'total_pages': result.total_pages
            }
        })
    finally:
        session.close()

@app.route('/api/videos', methods=['GET'])
def get_videos():
    video_svc, tag_svc, video_tag_svc, session = get_services()
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 50, type=int)
        search = request.args.get('search', None)
        
        result = video_svc.list_videos(
            page=page,
            page_size=page_size,
            search=search
        )
        
        thumbnail_gen = get_thumbnail_generator()
        
        videos = []
        for v in result.items:
            videos.append({
                'id': v.id,
                'title': v.title or os.path.basename(v.file_path),
                'file_path': v.file_path,
                'duration': v.duration,
                'tags': [{'id': t.id, 'name': t.name, 'parent_id': t.parent_id} for t in v.tags],
                'thumbnail': thumbnail_gen.get_thumbnail_url(v.id)
            })
        
        return jsonify({
            'success': True,
            'data': {
                'videos': videos,
                'total': result.total,
                'page': result.page,
                'page_size': result.page_size,
                'total_pages': result.total_pages
            }
        })
    finally:
        session.close()

@app.route('/api/videos/<int:video_id>', methods=['GET'])
def get_video_detail(video_id):
    video_svc, tag_svc, video_tag_svc, session = get_services()
    try:
        video = video_svc.get_video(video_id)
        return jsonify({
            'success': True,
            'data': {
                'id': video.id,
                'title': video.title or os.path.basename(video.file_path),
                'file_path': video.file_path,
                'duration': video.duration,
                'description': video.description,
                'tags': [{'id': t.id, 'name': t.name, 'parent_id': t.parent_id} for t in video.tags]
            }
        })
    finally:
        session.close()

@app.route('/api/videos/by-tags', methods=['POST'])
def get_videos_by_multiple_tags():
    video_svc, tag_svc, video_tag_svc, session = get_services()
    try:
        data = request.get_json()
        tag_ids = data.get('tag_ids', [])
        page = data.get('page', 1)
        page_size = data.get('page_size', 50)
        match_all = data.get('match_all', False)
        
        if not tag_ids:
            return jsonify({
                'success': True,
                'data': {
                    'videos': [],
                    'total': 0,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': 0
                }
            })
        
        result = video_svc.list_videos_by_tags(
            tag_ids=tag_ids,
            page=page,
            page_size=page_size,
            match_all=match_all
        )
        
        thumbnail_gen = get_thumbnail_generator()
        
        videos = []
        for v in result.items:
            videos.append({
                'id': v.id,
                'title': v.title or os.path.basename(v.file_path),
                'file_path': v.file_path,
                'duration': v.duration,
                'tags': [{'id': t.id, 'name': t.name, 'parent_id': t.parent_id} for t in v.tags],
                'thumbnail': thumbnail_gen.get_thumbnail_url(v.id)
            })
        
        return jsonify({
            'success': True,
            'data': {
                'videos': videos,
                'total': result.total,
                'page': result.page,
                'page_size': result.page_size,
                'total_pages': result.total_pages
            }
        })
    finally:
        session.close()

@app.route('/video/stream/<int:video_id>')
def serve_video_by_id(video_id):
    video_svc, tag_svc, video_tag_svc, session = get_services()
    try:
        video = video_svc.get_video(video_id)
        full_path = video.file_path
        
        if not os.path.exists(full_path):
            print(f"Video not found: {full_path}")
            return jsonify({'error': 'Video not found', 'path': full_path}), 404
        
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
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2)) if match.group(2) else file_size - 1
                
                length = end - start + 1
                
                def generate():
                    with open(full_path, 'rb') as f:
                        f.seek(start)
                        remaining = length
                        chunk_size = 64 * 1024
                        while remaining > 0:
                            chunk = f.read(min(chunk_size, remaining))
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            yield chunk
                
                response = Response(
                    generate(),
                    206,
                    mimetype=mimetype,
                    direct_passthrough=True
                )
                response.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
                response.headers.add('Accept-Ranges', 'bytes')
                response.headers.add('Content-Length', str(length))
                return response
        
        return send_file(full_path, mimetype=mimetype)
    finally:
        session.close()

@app.route('/api/video/stream/<int:video_id>')
def get_video_stream_url(video_id):
    video_svc, tag_svc, video_tag_svc, session = get_services()
    try:
        video = video_svc.get_video(video_id)
        file_path = video.file_path
        file_ext = os.path.splitext(file_path)[1].lower()
        
        stream_url = f'/video/stream/{video_id}'
        
        print(f"Stream URL: {stream_url}")
        print(f"File extension: {file_ext}")
        
        return jsonify({
            'success': True,
            'data': {
                'stream_url': stream_url,
                'title': video.title or os.path.basename(file_path),
                'duration': video.duration,
                'file_ext': file_ext
            }
        })
    finally:
        session.close()

@app.route('/api/stats')
def get_stats():
    video_svc, tag_svc, video_tag_svc, session = get_services()
    try:
        video_count = video_svc.count_videos()
        tag_count = tag_svc.count_tags()
        
        return jsonify({
            'success': True,
            'data': {
                'video_count': video_count,
                'tag_count': tag_count
            }
        })
    finally:
        session.close()

if __name__ == '__main__':
    update_thumbnails()
    app.run(host='0.0.0.0', port=5000, debug=True)
