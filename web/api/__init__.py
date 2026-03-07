"""
Web API模块

提供RESTful API接口，支持版本化管理。

API版本：
    - v1: 当前稳定版本API

路由结构：
    /api/v1/
    ├── /videos        # 视频相关API
    ├── /tags          # 标签相关API
    ├── /cache         # 缓存管理API
    └── /stats         # 统计数据API

使用示例：
    from web.api import api_v1_bp, register_api_v1_blueprints
    
    # 在应用中注册
    register_api_v1_blueprints(app)

响应格式：
    所有API返回统一的JSON格式：
    {
        "success": true/false,
        "message": "操作结果消息",
        "data": {...},
        "cached": true/false
    }
"""
from web.api.v1 import api_v1_bp, register_api_v1_blueprints

__all__ = ['api_v1_bp', 'register_api_v1_blueprints']
