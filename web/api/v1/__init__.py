"""
API v1 蓝图注册模块

注册API v1版本的所有子蓝图，统一管理API路由。

蓝图结构：
    /api/v1/
    ├── /videos        # videos_bp - 视频相关API
    ├── /tags          # tags_bp - 标签相关API
    ├── /cache         # cache_bp - 缓存管理API
    ├── /stats         # stats_bp - 统计数据API
    └── /tasks         # tasks_bp - 任务管理API

API文档：
    /api/docs          # Swagger UI 文档页面
    /api/openapi.yaml  # OpenAPI 规范文件

使用示例：
    from web.api.v1 import register_api_v1_blueprints
    
    # 在应用中注册
    register_api_v1_blueprints(app)
"""
from flask import Blueprint

from web.api.v1.videos import videos_bp
from web.api.v1.tags import tags_bp
from web.api.v1.cache import cache_bp
from web.api.v1.stats import stats_bp
from web.api.v1.tasks import tasks_bp
from web.api.docs import docs_bp

api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')


def register_api_v1_blueprints(app):
    """
    注册API v1蓝图
    
    将所有v1版本的子蓝图注册到api_v1_bp，
    然后将api_v1_bp注册到Flask应用。
    同时注册API文档蓝图。
    
    Args:
        app: Flask应用实例
    
    Example:
        app = Flask(__name__)
        register_api_v1_blueprints(app)
        # 现在可以访问 /api/v1/videos 等路由
        # 以及 /api/docs 文档页面
    """
    api_v1_bp.register_blueprint(videos_bp)
    api_v1_bp.register_blueprint(tags_bp)
    api_v1_bp.register_blueprint(cache_bp)
    api_v1_bp.register_blueprint(stats_bp)
    api_v1_bp.register_blueprint(tasks_bp)
    
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(docs_bp)
