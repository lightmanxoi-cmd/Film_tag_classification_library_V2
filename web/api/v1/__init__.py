"""
API v1 蓝图注册
"""
from flask import Blueprint

from web.api.v1.videos import videos_bp
from web.api.v1.tags import tags_bp
from web.api.v1.cache import cache_bp
from web.api.v1.stats import stats_bp

api_v1_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')


def register_api_v1_blueprints(app):
    """注册API v1蓝图"""
    api_v1_bp.register_blueprint(videos_bp)
    api_v1_bp.register_blueprint(tags_bp)
    api_v1_bp.register_blueprint(cache_bp)
    api_v1_bp.register_blueprint(stats_bp)
    
    app.register_blueprint(api_v1_bp)
