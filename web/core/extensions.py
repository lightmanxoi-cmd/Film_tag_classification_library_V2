"""
Flask扩展初始化模块

初始化和管理Flask扩展实例。

扩展列表：
    - cors: Flask-CORS跨域支持扩展

使用示例：
    from web.core.extensions import cors
    
    # 在应用中初始化（通过init_extensions统一调用）
    from web.core.extensions import init_extensions
    init_extensions(app)

CORS配置：
    通过应用配置控制CORS行为：
    - CORS_ORIGINS: 允许的来源（逗号分隔），'*'表示允许所有
    - CORS_METHODS: 允许的HTTP方法列表
    - CORS_ALLOW_HEADERS: 允许的请求头列表
    - CORS_MAX_AGE: 预检请求缓存时间（秒）

    开发环境默认允许所有来源，生产环境必须通过CORS_ORIGINS环境变量明确指定。
"""
from flask_cors import CORS

cors = CORS()


def init_extensions(app):
    """
    初始化所有Flask扩展

    根据应用配置初始化CORS等扩展。
    生产环境必须设置CORS_ORIGINS环境变量，否则将拒绝所有跨域请求。

    Args:
        app: Flask应用实例
    """
    origins = app.config.get('CORS_ORIGINS', '*')
    methods = app.config.get('CORS_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
    allow_headers = app.config.get('CORS_ALLOW_HEADERS', ['Content-Type', 'Authorization', 'X-Requested-With'])
    max_age = app.config.get('CORS_MAX_AGE', 600)

    if isinstance(origins, str):
        if origins.strip() == '':
            origins = []
        elif origins != '*':
            origins = [o.strip() for o in origins.split(',') if o.strip()]

    cors.init_app(
        app,
        resources={r"/api/*": {
            "origins": origins,
            "methods": methods,
            "allow_headers": allow_headers,
            "max_age": max_age
        }}
    )
