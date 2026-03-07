"""
认证模块

提供用户认证功能，包括登录验证、会话管理、密码修改等。

主要组件：
    - auth_bp: 认证路由蓝图
    - decorators: 认证装饰器
    - routes: 认证路由处理
    - service: 认证服务
    - init_auth: 初始化函数

使用示例：
    from web.auth import auth_bp, init_auth
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    
    # 初始化认证
    init_auth(app)

认证流程：
    1. 用户访问受保护页面
    2. login_required装饰器检查会话
    3. 未登录重定向到登录页
    4. 用户输入密码验证
    5. 验证成功设置会话
    6. 后续请求携带会话信息

安全特性：
    - Argon2密码哈希
    - 会话超时控制
    - CSRF保护
    - 安全Cookie设置
"""
from web.auth.routes import auth_bp, init_auth
from web.auth.decorators import login_required, api_login_required, optional_auth
from web.auth.service import AuthService

__all__ = [
    'auth_bp',
    'init_auth',
    'login_required',
    'api_login_required',
    'optional_auth',
    'AuthService'
]
