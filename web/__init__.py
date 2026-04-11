"""
Web模块

提供Flask Web应用的核心功能，包括应用工厂、服务管理、
API路由、页面路由、认证等。

主要组件：
    - app: Flask应用工厂
    - services: 服务上下文管理
    - api: RESTful API路由
    - pages: 页面路由
    - auth: 认证模块
    - core: 核心配置和工具

使用示例：
    from web import create_app, get_services
    
    # 创建应用
    app = create_app('production')
    
    # 运行应用
    app.run(host='0.0.0.0', port=5000)

模块结构：
    web/
    ├── __init__.py      # 模块入口
    ├── app.py           # 应用工厂
    ├── services.py      # 服务管理
    ├── auth.py          # 认证配置
    ├── api/             # API路由
    │   ├── v1/          # API v1版本
    │   └── __init__.py
    ├── auth/            # 认证模块
    │   ├── decorators.py
    │   ├── routes.py
    │   └── service.py
    ├── core/            # 核心模块
    │   ├── config.py
    │   ├── errors.py
    │   └── responses.py
    ├── pages/           # 页面路由
    └── static/          # 静态资源
"""
from web.app import create_app
from web.services import ServiceLocator, get_services
from video_tag_system.core.database import get_db_manager

__all__ = ['create_app', 'get_services', 'get_db_manager', 'ServiceLocator']
