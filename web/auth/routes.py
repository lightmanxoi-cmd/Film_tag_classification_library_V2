"""
认证路由蓝图模块

提供认证相关的路由处理。

路由列表：
    GET    /login           # 登录页面
    POST   /login           # 登录处理
    GET    /logout          # 登出
    POST   /api/v1/change-password  # 修改密码

功能特点：
    - 基于Argon2的密码验证
    - 会话管理和超时控制
    - CSRF保护
    - 初始密码设置

使用示例：
    # 在应用中注册
    from web.auth import auth_bp
    app.register_blueprint(auth_bp)

初始密码：
    首次运行时自动设置默认密码：13245768
    请登录后及时修改密码！
"""
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, session

from web.auth.service import AuthService, init_default_password, get_session_secret
from web.auth.decorators import login_required
from web.core.responses import APIResponse

auth_bp = Blueprint('auth', __name__)

auth_service = AuthService()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    登录页面和登录处理
    
    GET: 显示登录页面
    POST: 处理登录请求
    
    Features:
        - 已登录用户自动跳转主页
        - 密码验证成功设置会话
        - 支持next参数跳转
        - CSRF令牌保护
    
    Query Parameters:
        next: 登录后跳转的URL
    
    Returns:
        GET: 登录页面HTML
        POST: 重定向到主页或next参数指定的URL
    
    Example:
        GET /login
        GET /login?next=/dashboard
        POST /login (password=xxx)
    """
    if session.get('authenticated', False):
        return redirect(url_for('pages.index'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        
        if auth_service.verify(password):
            session['authenticated'] = True
            session.permanent = True
            next_url = request.args.get('next') or url_for('pages.index')
            return redirect(next_url)
        else:
            return render_template('login.html', 
                                   csrf_token=secrets.token_hex(16),
                                   error=True)
    
    return render_template('login.html', 
                           csrf_token=secrets.token_hex(16),
                           error=False)


@auth_bp.route('/logout')
def logout():
    """
    登出
    
    清除会话并重定向到登录页。
    
    Returns:
        重定向到登录页
    
    Example:
        GET /logout
    """
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/v1/change-password', methods=['POST'])
@login_required
def change_password():
    """
    修改密码API
    
    验证原密码并设置新密码。
    
    Request Body:
        old_password: 原密码
        new_password: 新密码（至少6位）
    
    Returns:
        JSON响应，包含操作结果
    
    Example:
        POST /api/v1/change-password
        {
            "old_password": "13245768",
            "new_password": "newpassword123"
        }
        
        Response:
        {
            "success": true,
            "message": "密码修改成功"
        }
    """
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    success, message = auth_service.change_password(old_password, new_password)
    
    if success:
        return APIResponse.success(message=message)
    else:
        return APIResponse.error(message=message)


def init_auth(app):
    """
    初始化认证模块
    
    设置应用密钥和会话配置，初始化默认密码。
    会话密钥从环境变量 SESSION_SECRET/SECRET_KEY 读取。
    
    Args:
        app: Flask应用实例
    
    Returns:
        dict: 认证配置字典
    
    Side Effects:
        - 设置app.secret_key（从环境变量读取）
        - 首次运行时创建默认密码
    
    Environment Variables:
        SESSION_SECRET: 会话密钥（推荐，优先级最高）
        SECRET_KEY: 应用密钥（兼容）
    
    Example:
        from web.auth import init_auth
        config = init_auth(app)
    """
    config, is_new = init_default_password(app.root_path)
    
    app.secret_key = get_session_secret()
    
    if is_new:
        print("=" * 50)
        print("安全登录系统已启用")
        print("初始密码: 13245768")
        print("请登录后及时修改密码！")
        print("=" * 50)
    
    return config
