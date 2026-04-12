"""
Flask扩展初始化模块

初始化和管理Flask扩展实例。

扩展列表：
    - cors: Flask-CORS跨域支持扩展

使用示例：
    from web.core.extensions import cors
    
    # 在应用中初始化
    cors.init_app(app)

CORS配置：
    通过环境变量 CORS_ORIGINS 控制允许的来源：
    - 未设置或 "*" : 允许所有来源（开发环境）
    - 多个域名用逗号分隔 : "http://localhost:3000,https://example.com"
    
    生产环境建议设置具体的域名列表。
"""
import os
from flask_cors import CORS

cors = CORS()


def get_cors_origins():
    """
    获取CORS允许的来源列表
    
    从环境变量 CORS_ORIGINS 读取配置：
    - 未设置或 "*" : 返回 "*"（允许所有）
    - 逗号分隔的域名 : 返回域名列表
    
    Returns:
        str | list: 允许的来源
    """
    origins = os.environ.get('CORS_ORIGINS', '*')
    
    if origins == '*':
        return '*'
    
    return [origin.strip() for origin in origins.split(',') if origin.strip()]


def init_cors(app):
    """
    初始化CORS扩展
    
    根据环境变量配置CORS允许的来源。
    
    Args:
        app: Flask应用实例
    """
    origins = get_cors_origins()
    
    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True
            }
        }
    )
    
    if origins == '*':
        app.logger.warning("CORS已配置为允许所有来源，生产环境建议设置 CORS_ORIGINS 环境变量")
    else:
        app.logger.info(f"CORS已配置为允许来源: {origins}")
