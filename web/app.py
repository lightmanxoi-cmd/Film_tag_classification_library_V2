"""
Flask应用工厂模块

使用应用工厂模式创建Flask应用实例，支持多环境配置。
提供数据库管理、缓存清理、请求钩子、异步任务管理等功能。

主要功能：
    - create_app: 应用工厂函数，创建并配置Flask应用
    - get_db_manager: 获取数据库管理器单例

应用结构：
    - 扩展初始化：CORS跨域支持
    - 认证初始化：基于Argon2的密码认证
    - 蓝图注册：API、页面、认证模块
    - 请求钩子：数据库会话管理、缓存清理
    - 错误处理：统一异常处理
    - 异步任务：后台任务管理器

使用示例：
    # 创建应用
    app = create_app('development')
    
    # 运行应用
    app.run(host='0.0.0.0', port=5000)

配置环境：
    - development: 开发环境，启用调试和SQL日志
    - production: 生产环境，启用安全配置和日志
    - testing: 测试环境，使用内存数据库

Attributes:
    db_manager: 数据库管理器单例
    query_cache: 查询缓存实例
    _last_cache_cleanup: 上次缓存清理时间
    CACHE_CLEANUP_INTERVAL: 缓存清理间隔（秒）
"""
import os
import time
import atexit
from flask import Flask, g, request

from video_tag_system.core.database import DatabaseManager
from video_tag_system.core.backup_scheduler import init_backup_scheduler, stop_backup_scheduler
from video_tag_system.utils.cache import query_cache
from video_tag_system.utils.logger import get_logger, setup_logging, set_request_id, clear_request_id
from video_tag_system.utils.async_tasks import init_task_manager, get_task_manager

logger = get_logger(__name__)

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
    """
    获取数据库管理器单例
    
    创建或返回全局数据库管理器实例。
    首次调用时会创建表结构。
    
    Returns:
        DatabaseManager: 数据库管理器实例
    
    Example:
        db = get_db_manager()
        session = db.session_factory()
    """
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
    
    创建并配置Flask应用实例。按照以下顺序初始化：
    1. 加载配置
    2. 初始化扩展
    3. 初始化认证
    4. 注册蓝图
    5. 注册请求钩子
    6. 注册错误处理器
    7. 初始化数据库
    8. 注册清理函数
    
    Args:
        config_name: 配置名称
            - 'development': 开发环境
            - 'production': 生产环境
            - 'testing': 测试环境
            - None: 从环境变量FLASK_ENV读取，默认'default'
    
    Returns:
        Flask: 配置完成的Flask应用实例
    
    Example:
        # 开发环境
        app = create_app('development')
        
        # 生产环境
        app = create_app('production')
        
        # 从环境变量读取
        export FLASK_ENV=production
        app = create_app()
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
    """
    初始化Flask扩展
    
    初始化CORS等Flask扩展。
    
    Args:
        app: Flask应用实例
    """
    cors.init_app(app)


def _init_auth(app: Flask):
    """
    初始化认证模块
    
    设置应用密钥和会话配置。
    
    Args:
        app: Flask应用实例
    """
    init_auth(app)


def _register_blueprints(app: Flask):
    """
    注册蓝图
    
    注册所有应用蓝图：
    - auth_bp: 认证相关路由
    - pages_bp: 页面路由
    - api_v1: API v1版本路由
    
    同时注册兼容旧API的路由。
    
    Args:
        app: Flask应用实例
    """
    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    register_api_v1_blueprints(app)
    
    _register_legacy_routes(app)


def _register_legacy_routes(app: Flask):
    """
    注册兼容旧API的路由
    
    为保持向后兼容，将旧版API路由重定向到新版API。
    旧版路由格式：/api/xxx
    新版路由格式：/api/v1/xxx
    
    Args:
        app: Flask应用实例
    
    Note:
        这些路由将在未来版本中移除，请使用新版API。
    """
    
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
    """
    注册请求钩子
    
    设置请求前后的处理逻辑：
    - before_request: 初始化请求上下文、定期清理缓存
    - teardown_request: 清理数据库会话
    - after_request: 确保ES6模块正确的MIME类型
    
    Args:
        app: Flask应用实例
    """
    
    @app.before_request
    def before_request():
        """
        请求前处理
        
        初始化请求上下文变量，定期清理过期缓存。
        """
        set_request_id()
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
                logger.debug(f"缓存清理: 移除了 {cleaned} 个过期条目")
    
    @app.after_request
    def after_request(response):
        """
        请求后处理
        
        确保JavaScript文件使用正确的MIME类型，
        特别是ES6模块需要 application/javascript。
        """
        if response.content_type and 'javascript' in response.content_type:
            if request.path.endswith('.js'):
                response.content_type = 'application/javascript; charset=utf-8'
        return response
    
    @app.teardown_request
    def teardown_request(exception=None):
        """
        请求后处理
        
        清理数据库会话，发生异常时回滚事务。
        
        Args:
            exception: 请求过程中发生的异常，无异常时为None
        """
        session = getattr(g, 'db_session', None)
        if session is not None:
            try:
                if exception:
                    session.rollback()
                session.close()
            except Exception:
                pass


def _init_database(app: Flask):
    """
    初始化数据库
    
    创建数据库管理器实例，确保表结构存在。
    同时初始化每日备份调度器和异步任务管理器。
    
    Args:
        app: Flask应用实例
    """
    db = get_db_manager()
    
    try:
        init_backup_scheduler(db)
        logger.info("备份调度器初始化完成")
    except Exception as e:
        logger.warning(f"备份调度器初始化失败: {e}")
    
    try:
        init_task_manager(max_workers=4, task_timeout=3600)
        logger.info("异步任务管理器初始化完成")
    except Exception as e:
        logger.warning(f"异步任务管理器初始化失败: {e}")


def _register_cleanup(app: Flask):
    """
    注册清理函数
    
    应用退出时清理缓存、停止备份调度器、关闭任务管理器等资源。
    
    Args:
        app: Flask应用实例
    """
    
    def cleanup_on_exit():
        """应用退出时的清理函数"""
        try:
            stop_backup_scheduler()
            logger.info("备份调度器已停止")
        except Exception as e:
            logger.warning(f"停止备份调度器失败: {e}")
        
        try:
            task_mgr = get_task_manager()
            task_mgr.shutdown(wait=False)
            logger.info("异步任务管理器已关闭")
        except Exception as e:
            logger.warning(f"关闭异步任务管理器失败: {e}")
        
        try:
            query_cache.clear()
            logger.info("缓存已清理")
        except Exception as e:
            logger.warning(f"清理缓存失败: {e}")
    
    atexit.register(cleanup_on_exit)
