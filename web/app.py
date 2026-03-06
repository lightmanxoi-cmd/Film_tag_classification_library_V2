"""
Flask应用工厂
"""
import os
import time
import atexit
from flask import Flask, g

from video_tag_system.core.database import DatabaseManager
from video_tag_system.utils.cache import query_cache

from web.core.config import config
from web.core.extensions import cors
from web.core.errors import register_error_handlers
from web.auth import auth_bp, init_auth
from web.pages import pages_bp
from web.api import register_api_v1_blueprints


db_manager = None
_last_cache_cleanup = time.time()
CACHE_CLEANUP_INTERVAL = 300


def get_db_manager():
    """获取数据库管理器单例"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager(
            database_url=config['default'].DATABASE_URL,
            echo=config['default'].DATABASE_ECHO
        )
        db_manager.create_tables()
    return db_manager


def create_app(config_name: str = None) -> Flask:
    """
    Flask应用工厂函数
    
    Args:
        config_name: 配置名称 ('development', 'production', 'testing')
    
    Returns:
        Flask应用实例
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(
        __name__,
        static_folder='static',
        template_folder='templates'
    )
    
    app_config = config.get(config_name, config['default'])
    app.config.from_object(app_config)
    
    if hasattr(app_config, 'init_app'):
        app_config.init_app(app)
    
    _init_extensions(app)
    _init_auth(app)
    _register_blueprints(app)
    _register_request_hooks(app)
    register_error_handlers(app)
    _init_database(app)
    
    _register_cleanup(app)
    
    return app


def _init_extensions(app: Flask):
    """初始化Flask扩展"""
    cors.init_app(app)


def _init_auth(app: Flask):
    """初始化认证模块"""
    init_auth(app)


def _register_blueprints(app: Flask):
    """注册蓝图"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    register_api_v1_blueprints(app)
    
    _register_legacy_routes(app)


def _register_legacy_routes(app: Flask):
    """注册兼容旧API的路由（保持向后兼容）"""
    
    @app.route('/video/stream/<int:video_id>')
    def legacy_video_stream(video_id):
        """兼容旧的视频流路由"""
        from flask import redirect
        return redirect(f'/api/v1/videos/stream/{video_id}')
    
    @app.route('/api/tags/tree', methods=['GET'])
    def legacy_tags_tree():
        """兼容旧的标签树路由"""
        from flask import redirect
        return redirect(f'/api/v1/tags/tree')
    
    @app.route('/api/tags/<int:tag_id>/videos', methods=['GET'])
    def legacy_tags_videos(tag_id):
        """兼容旧的标签视频路由"""
        from flask import redirect, request
        query_string = request.query_string.decode('utf-8')
        url = f'/api/v1/tags/{tag_id}/videos'
        if query_string:
            url += f'?{query_string}'
        return redirect(url)
    
    @app.route('/api/videos', methods=['GET'])
    def legacy_videos_list():
        """兼容旧的视频列表路由"""
        from flask import redirect, request
        query_string = request.query_string.decode('utf-8')
        url = '/api/v1/videos'
        if query_string:
            url += f'?{query_string}'
        return redirect(url)
    
    @app.route('/api/videos/<int:video_id>', methods=['GET'])
    def legacy_video_detail(video_id):
        """兼容旧的视频详情路由"""
        from flask import redirect
        return redirect(f'/api/v1/videos/{video_id}')
    
    @app.route('/api/videos/by-tags', methods=['POST'])
    def legacy_videos_by_tags():
        """兼容旧的标签视频搜索路由"""
        from flask import request, jsonify
        from web.api.v1.videos import get_videos_by_multiple_tags
        return get_videos_by_multiple_tags()
    
    @app.route('/api/videos/by-tags-advanced', methods=['POST'])
    def legacy_videos_by_tags_advanced():
        """兼容旧的高级标签搜索路由"""
        from flask import request, jsonify
        from web.api.v1.videos import get_videos_by_tags_advanced
        return get_videos_by_tags_advanced()
    
    @app.route('/api/video/stream/<int:video_id>')
    def legacy_video_stream_url(video_id):
        """兼容旧的视频流URL路由"""
        from flask import redirect
        return redirect(f'/api/v1/videos/{video_id}/stream-url')
    
    @app.route('/api/stats')
    def legacy_stats():
        """兼容旧的统计路由"""
        from flask import redirect
        return redirect('/api/v1/stats')
    
    @app.route('/api/cache/stats')
    def legacy_cache_stats():
        """兼容旧的缓存统计路由"""
        from flask import redirect
        return redirect('/api/v1/cache/stats')
    
    @app.route('/api/cache/clear', methods=['POST'])
    def legacy_cache_clear():
        """兼容旧的缓存清除路由"""
        from web.api.v1.cache import clear_cache
        return clear_cache()
    
    @app.route('/api/cache/invalidate/<key_prefix>', methods=['POST'])
    def legacy_cache_invalidate(key_prefix):
        """兼容旧的缓存失效路由"""
        from web.api.v1.cache import invalidate_cache
        return invalidate_cache(key_prefix)
    
    @app.route('/api/generate-gif/<int:video_id>', methods=['POST'])
    def legacy_generate_gif(video_id):
        """兼容旧的GIF生成路由"""
        from web.api.v1.videos import generate_gif_for_video
        return generate_gif_for_video(video_id)
    
    @app.route('/api/change-password', methods=['POST'])
    def legacy_change_password():
        """兼容旧的密码修改路由"""
        from web.auth.routes import change_password
        return change_password()


def _register_request_hooks(app: Flask):
    """注册请求钩子"""
    
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


def _init_database(app: Flask):
    """初始化数据库"""
    get_db_manager()


def _register_cleanup(app: Flask):
    """注册清理函数"""
    
    def cleanup_on_exit():
        try:
            query_cache.clear()
            print("Cache cleared on exit")
        except Exception:
            pass
    
    atexit.register(cleanup_on_exit)
