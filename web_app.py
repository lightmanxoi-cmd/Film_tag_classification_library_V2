"""
奈飞风格视频播放网站 - Flask后端
包含安全的登录认证系统
优化：Session管理、缓存机制、内存优化
"""
import os
import re
import secrets
import time
import atexit
import threading
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_file, render_template, Response, redirect, url_for, session, g
from flask_cors import CORS
from video_tag_system.core.database import DatabaseManager
from video_tag_system.services.video_service import VideoService
from video_tag_system.services.tag_service import TagService
from video_tag_system.services.video_tag_service import VideoTagService
from video_tag_system.utils.thumbnail_generator import get_thumbnail_generator
from video_tag_system.utils.cache import get_cache, CACHE_KEYS, query_cache
from sqlalchemy import text
from functools import wraps

INACTIVITY_TIMEOUT = 1800
CACHE_CLEANUP_INTERVAL = 300

app = Flask(__name__, 
            static_folder='web/static',
            template_folder='web/templates')

app.secret_key = secrets.token_hex(32)
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400

CORS(app)

db_manager = DatabaseManager(database_url="sqlite:///./video_library.db", echo=False)
db_manager.create_tables()

VIDEO_BASE_PATH = "F:\\666"

AUTH_CONFIG_FILE = '.auth_config.json'

_last_cache_cleanup = time.time()

def get_auth_config_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), AUTH_CONFIG_FILE)

def load_auth_config():
    config_path = get_auth_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                import json
                return json.load(f)
        except Exception:
            pass
    return {}

def save_auth_config(config):
    config_path = get_auth_config_path()
    try:
        import json
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存认证配置失败: {e}")

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, VerificationError
    ARGON2_AVAILABLE = True
    ph = PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16
    )
except ImportError:
    ARGON2_AVAILABLE = False
    import hashlib
    import hmac
    ph = None
    print("警告: argon2-cffi 未安装，将使用 PBKDF2-SHA256 作为后备方案")
    print("建议运行: pip install argon2-cffi")

def hash_password(password: str) -> str:
    if ARGON2_AVAILABLE:
        return ph.hash(password)
    else:
        salt = os.urandom(32)
        iterations = 100000
        hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            iterations
        )
        return f"pbkdf2_sha256${iterations}${salt.hex()}${hash_bytes.hex()}"

def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    
    if ARGON2_AVAILABLE:
        try:
            ph.verify(password_hash, password)
            return True
        except (VerifyMismatchError, VerificationError):
            return False
    else:
        try:
            parts = password_hash.split('$')
            if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
                return False
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            stored_hash = parts[3]
            computed_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                iterations
            ).hex()
            return hmac.compare_digest(stored_hash, computed_hash)
        except Exception:
            return False

def init_default_password():
    config = load_auth_config()
    if not config.get('password_hash'):
        default_password = '13245768'
        password_hash = hash_password(default_password)
        config['password_hash'] = password_hash
        config['session_secret'] = secrets.token_hex(32)
        save_auth_config(config)
        print(f"已设置默认密码: {default_password}")
        print("请登录后及时修改密码！")
    return config

auth_config = init_default_password()
if auth_config.get('session_secret'):
    app.secret_key = auth_config['session_secret']

@app.before_request
def before_request():
    g.db_session = None
    g.video_service = None
    g.tag_service = None
    g.video_tag_service = None
    g.request_start_time = time.time()
    
    global _last_cache_cleanup
    if time.time() - _last_cache_cleanup > CACHE_CLEANUP_INTERVAL:
        _last_cache_cleanup = time.time()
        cleaned = query_cache.cleanup_expired()
        if cleaned > 0:
            print(f"Cache cleanup: removed {cleaned} expired entries")

@app.teardown_request
def teardown_request(exception=None):
    session = getattr(g, 'db_session', None)
    if session is not None:
        try:
            if exception:
                session.rollback()
            session.close()
        except Exception:
            pass

def get_db_session():
    if g.db_session is None:
        g.db_session = db_manager.session_factory()
    return g.db_session

def get_video_service():
    if g.video_service is None:
        g.video_service = VideoService(get_db_session())
    return g.video_service

def get_tag_service():
    if g.tag_service is None:
        g.tag_service = TagService(get_db_session())
    return g.tag_service

def get_video_tag_service():
    if g.video_tag_service is None:
        g.video_tag_service = VideoTagService(get_db_session())
    return g.video_tag_service

def get_services():
    return (
        get_video_service(),
        get_tag_service(),
        get_video_tag_service(),
        get_db_session()
    )

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated', False):
            if request.path.startswith('/api/') or request.path.startswith('/video/'):
                return jsonify({'success': False, 'error': '未授权访问，请先登录'}), 401
            return redirect(url_for('login'))
        
        last_activity = session.get('last_activity')
        if last_activity:
            elapsed = time.time() - last_activity
            if elapsed > INACTIVITY_TIMEOUT:
                session.clear()
                if request.path.startswith('/api/') or request.path.startswith('/video/'):
                    return jsonify({'success': False, 'error': '登录已过期，请重新登录', 'timeout': True}), 401
                return redirect(url_for('login'))
        
        session['last_activity'] = time.time()
        session.modified = True
        
        return f(*args, **kwargs)
    return decorated_function

def update_thumbnails():
    print("=" * 50)
    print("Checking video thumbnails and GIF previews...")
    
    thumbnail_gen = get_thumbnail_generator()
    db_session = db_manager.session_factory()
    
    try:
        result = db_session.execute(text("SELECT id, file_path, title, duration FROM videos")).fetchall()
        videos = [(row[0], row[1], row[2]) for row in result]
        videos_with_duration = [(row[0], row[1], row[2], row[3]) for row in result]
        
        print(f"Total videos: {len(videos)}")
        
        missing = thumbnail_gen.get_missing_thumbnails(videos)
        
        if not missing:
            print("All videos have thumbnails.")
        else:
            print(f"Found {len(missing)} videos without thumbnails, generating...")
            results = thumbnail_gen.batch_generate(missing, max_workers=2, force=False)
            print(f"Thumbnail generation complete: Success {results['success']}, Failed {results['failed']}")
        
        missing_gifs = thumbnail_gen.get_missing_gifs(videos)
        
        if not missing_gifs:
            print("All videos have GIF previews.")
        else:
            print(f"Found {len(missing_gifs)} videos without GIF previews, generating...")
            gif_videos = [(v[0], v[1], v[2], None) for v in missing_gifs]
            results = thumbnail_gen.batch_generate_gifs(gif_videos, max_workers=1, force=False)
            print(f"GIF generation complete: Success {results['success']}, Failed {results['failed']}, Skipped {results['skipped']}")
    except Exception as e:
        print(f"Error updating thumbnails/GIFs: {e}")
    finally:
        db_session.close()
    
    print("=" * 50)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('authenticated', False):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        config = load_auth_config()
        stored_hash = config.get('password_hash', '')
        
        if verify_password(password, stored_hash):
            session['authenticated'] = True
            session['last_activity'] = time.time()
            session.permanent = True
            next_url = request.args.get('next') or url_for('index')
            return redirect(next_url)
        else:
            return render_template('login.html', 
                                   csrf_token=secrets.token_hex(16),
                                   error=True)
    
    return render_template('login.html', 
                           csrf_token=secrets.token_hex(16),
                           error=False)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/clock-wallpaper')
@login_required
def clock_wallpaper():
    return render_template('clock_wallpaper.html')

@app.route('/multi-play')
@login_required
def multi_play():
    return render_template('multi_play.html')

@app.route('/random-recommend')
@login_required
def random_recommend():
    return render_template('random_recommend.html')

@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    if not old_password or not new_password:
        return jsonify({'success': False, 'error': '请填写完整信息'})
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'error': '新密码长度至少6位'})
    
    config = load_auth_config()
    stored_hash = config.get('password_hash', '')
    
    if not verify_password(old_password, stored_hash):
        return jsonify({'success': False, 'error': '原密码错误'})
    
    new_hash = hash_password(new_password)
    config['password_hash'] = new_hash
    save_auth_config(config)
    
    return jsonify({'success': True, 'message': '密码修改成功'})

@app.route('/api/tags/tree', methods=['GET'])
@login_required
def get_tag_tree():
    cache = get_cache()
    cache_key = CACHE_KEYS['tag_tree']
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify({'success': True, 'data': cached_result, 'cached': True})
    
    video_svc, tag_svc, video_tag_svc, _ = get_services()
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
        
        cache.set(cache_key, result, ttl=120)
        return jsonify({'success': True, 'data': result, 'cached': False})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tags/<int:tag_id>/videos', methods=['GET'])
@login_required
def get_videos_by_tag(tag_id):
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    
    cache = get_cache()
    cache_key = f"videos:tag:{tag_id}:page:{page}:size:{page_size}"
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify({'success': True, 'data': cached_result, 'cached': True})
    
    video_svc, tag_svc, video_tag_svc, _ = get_services()
    try:
        result = video_svc.list_videos_by_tags(
            tag_ids=[tag_id],
            page=page,
            page_size=page_size,
            match_all=False
        )
        
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
        return jsonify({'success': True, 'data': response_data, 'cached': False})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/videos', methods=['GET'])
@login_required
def get_videos():
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    search = request.args.get('search', None)
    random_order = request.args.get('random', 'true').lower() == 'true'
    random_seed = request.args.get('seed', None, type=int)
    
    cache = get_cache()
    cache_key = f"videos:list:page:{page}:size:{page_size}:search:{search or ''}:random:{random_order}:seed:{random_seed or 0}"
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify({'success': True, 'data': cached_result, 'cached': True})
    
    video_svc, tag_svc, video_tag_svc, _ = get_services()
    try:
        result = video_svc.list_videos(
            page=page,
            page_size=page_size,
            search=search,
            random_order=random_order,
            random_seed=random_seed
        )
        
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
        return jsonify({'success': True, 'data': response_data, 'cached': False})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/videos/<int:video_id>', methods=['GET'])
@login_required
def get_video_detail(video_id):
    cache = get_cache()
    cache_key = f"{CACHE_KEYS['video_by_id']}:{video_id}"
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify({'success': True, 'data': cached_result, 'cached': True})
    
    video_svc, _, _, _ = get_services()
    try:
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
        return jsonify({'success': True, 'data': response_data, 'cached': False})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/videos/by-tags', methods=['POST'])
@login_required
def get_videos_by_multiple_tags():
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
    
    cache = get_cache()
    tag_ids_str = ','.join(map(str, sorted(tag_ids)))
    cache_key = f"videos:by_tags:{tag_ids_str}:page:{page}:size:{page_size}:all:{match_all}"
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify({'success': True, 'data': cached_result, 'cached': True})
    
    video_svc, tag_svc, video_tag_svc, _ = get_services()
    try:
        result = video_svc.list_videos_by_tags(
            tag_ids=tag_ids,
            page=page,
            page_size=page_size,
            match_all=match_all
        )
        
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
        return jsonify({'success': True, 'data': response_data, 'cached': False})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/videos/by-tags-advanced', methods=['POST'])
@login_required
def get_videos_by_tags_advanced():
    data = request.get_json()
    tags_by_category = data.get('tags_by_category', {})
    page = data.get('page', 1)
    page_size = data.get('page_size', 50)
    
    if not tags_by_category:
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
    
    cache = get_cache()
    category_str = str(sorted([(k, sorted(v)) for k, v in tags_by_category.items()]))
    cache_key = f"videos:advanced:{hash(category_str)}:page:{page}:size:{page_size}"
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify({'success': True, 'data': cached_result, 'cached': True})
    
    video_svc, tag_svc, video_tag_svc, _ = get_services()
    try:
        result = video_svc.list_videos_by_tags_advanced(
            tags_by_category=tags_by_category,
            page=page,
            page_size=page_size
        )
        
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
        return jsonify({'success': True, 'data': response_data, 'cached': False})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/video/stream/<int:video_id>')
@login_required
def serve_video_by_id(video_id):
    video_svc, _, _, _ = get_services()
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/stream/<int:video_id>')
@login_required
def get_video_stream_url(video_id):
    video_svc, _, _, _ = get_services()
    try:
        video = video_svc.get_video(video_id)
        file_path = video.file_path
        file_ext = os.path.splitext(file_path)[1].lower()
        
        stream_url = f'/video/stream/{video_id}'
        
        return jsonify({
            'success': True,
            'data': {
                'stream_url': stream_url,
                'title': video.title or os.path.basename(file_path),
                'duration': video.duration,
                'file_ext': file_ext
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats')
@login_required
def get_stats():
    cache = get_cache()
    cache_key = CACHE_KEYS['stats']
    
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify({'success': True, 'data': cached_result, 'cached': True})
    
    video_svc, tag_svc, _, _ = get_services()
    try:
        video_count = video_svc.count_videos()
        tag_count = tag_svc.count_tags()
        
        result = {
            'video_count': video_count,
            'tag_count': tag_count
        }
        
        cache.set(cache_key, result, ttl=60)
        return jsonify({'success': True, 'data': result, 'cached': False})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cache/stats')
@login_required
def get_cache_stats():
    cache = get_cache()
    thumbnail_gen = get_thumbnail_generator()
    
    query_stats = cache.get_stats()
    thumbnail_stats = thumbnail_gen.get_cache_stats()
    
    return jsonify({
        'success': True,
        'data': {
            'query_cache': query_stats,
            'thumbnail_cache': thumbnail_stats
        }
    })

@app.route('/api/cache/clear', methods=['POST'])
@login_required
def clear_cache():
    cache = get_cache()
    cache.clear()
    
    return jsonify({
        'success': True,
        'message': 'Cache cleared successfully'
    })

@app.route('/api/cache/invalidate/<key_prefix>', methods=['POST'])
@login_required
def invalidate_cache_endpoint(key_prefix):
    cache = get_cache()
    count = cache.delete_pattern(key_prefix)
    
    return jsonify({
        'success': True,
        'message': f'Invalidated {count} cache entries',
        'count': count
    })

@app.route('/api/generate-gif/<int:video_id>', methods=['POST'])
@login_required
def generate_gif_for_video(video_id):
    video_svc, _, _, _ = get_services()
    try:
        video = video_svc.get_video(video_id)
        video_title = video.title or os.path.basename(video.file_path)
        
        thumbnail_gen = get_thumbnail_generator()
        
        if thumbnail_gen.has_gif(video_title):
            return jsonify({
                'success': True,
                'message': 'GIF already exists',
                'gif_url': thumbnail_gen.get_gif_url(video_title)
            })
        
        result = thumbnail_gen.generate_gif(video.file_path, video_title, video.duration)
        
        if result:
            return jsonify({
                'success': True,
                'message': 'GIF generated successfully',
                'gif_url': thumbnail_gen.get_gif_url(video_title)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to generate GIF'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def create_app():
    return app

def cleanup_on_exit():
    try:
        query_cache.clear()
        print("Cache cleared on exit")
    except Exception:
        pass

atexit.register(cleanup_on_exit)

if __name__ == '__main__':
    print("=" * 50)
    print("安全登录系统已启用")
    print("初始密码: 13245768")
    print("请登录后及时修改密码！")
    print("=" * 50)
    update_thumbnails()
    
    try:
        from waitress import serve
        print("使用 Waitress 生产服务器启动...")
        print("访问地址: http://0.0.0.0:5000")
        print("按 Ctrl+C 停止服务器")
        print("=" * 50)
        serve(
            app,
            host='0.0.0.0',
            port=5000,
            threads=16,
            connection_limit=200,
            channel_timeout=300,
            max_request_body_size=10737418240,
            cleanup_interval=60
        )
    except ImportError:
        print("警告: waitress 未安装，使用 Flask 开发服务器")
        print("建议运行: pip install waitress")
        print("=" * 50)
        app.run(host='0.0.0.0', port=5000, debug=True)
