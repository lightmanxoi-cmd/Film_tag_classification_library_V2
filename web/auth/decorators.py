"""
认证装饰器模块

提供登录验证和会话管理的装饰器。

主要功能：
    - login_required: 登录验证装饰器
    - api_login_required: API专用登录验证装饰器
    - optional_auth: 可选认证装饰器

会话管理：
    - 检查session中的认证状态
    - 检查会话超时（默认30分钟）
    - 更新最后活动时间

使用示例：
    from web.auth.decorators import login_required
    
    @app.route('/protected')
    @login_required
    def protected_route():
        return "已登录用户可见"
    
    @app.route('/api/data')
    @api_login_required
    def api_data():
        return jsonify({'data': 'value'})

响应类型：
    - Web页面: 未登录重定向到登录页
    - API接口: 返回401 JSON错误响应
"""
import time
from functools import wraps
from flask import request, jsonify, redirect, url_for, session, g

INACTIVITY_TIMEOUT = 1800


def login_required(f):
    """
    登录验证装饰器
    
    验证用户是否已登录，检查会话是否超时。
    - Web页面请求：未登录重定向到登录页
    - API请求：返回401 JSON错误
    
    Features:
        - 检查session['authenticated']状态
        - 检查会话超时（INACTIVITY_TIMEOUT秒）
        - 更新最后活动时间
    
    Args:
        f: 被装饰的函数
    
    Returns:
        装饰后的函数
    
    Example:
        @app.route('/dashboard')
        @login_required
        def dashboard():
            return render_template('dashboard.html')
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated', False):
            if request.path.startswith('/api/') or request.path.startswith('/video/'):
                return jsonify({
                    'success': False, 
                    'error': '未授权访问，请先登录'
                }), 401
            return redirect(url_for('auth.login'))
        
        last_activity = session.get('last_activity')
        if last_activity:
            elapsed = time.time() - last_activity
            if elapsed > INACTIVITY_TIMEOUT:
                session.clear()
                if request.path.startswith('/api/') or request.path.startswith('/video/'):
                    return jsonify({
                        'success': False, 
                        'error': '登录已过期，请重新登录', 
                        'timeout': True
                    }), 401
                return redirect(url_for('auth.login'))
        
        session['last_activity'] = time.time()
        session.modified = True
        
        return f(*args, **kwargs)
    return decorated_function


def api_login_required(f):
    """
    API专用登录验证装饰器
    
    与login_required类似，但只返回JSON响应，不进行重定向。
    适用于纯API接口的认证。
    
    Features:
        - 检查session['authenticated']状态
        - 检查会话超时
        - 返回标准JSON错误响应
        - 包含错误码便于客户端处理
    
    Args:
        f: 被装饰的函数
    
    Returns:
        装饰后的函数
    
    Example:
        @app.route('/api/user/profile')
        @api_login_required
        def get_profile():
            return jsonify({'profile': {...}})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated', False):
            return jsonify({
                'success': False, 
                'error': '未授权访问，请先登录',
                'error_code': 'UNAUTHORIZED'
            }), 401
        
        last_activity = session.get('last_activity')
        if last_activity:
            elapsed = time.time() - last_activity
            if elapsed > INACTIVITY_TIMEOUT:
                session.clear()
                return jsonify({
                    'success': False, 
                    'error': '登录已过期，请重新登录', 
                    'timeout': True,
                    'error_code': 'SESSION_EXPIRED'
                }), 401
        
        session['last_activity'] = time.time()
        session.modified = True
        
        return f(*args, **kwargs)
    return decorated_function


def optional_auth(f):
    """
    可选认证装饰器
    
    如果用户已登录则更新活动时间，未登录也允许访问。
    适用于需要区分登录/未登录状态的公开接口。
    
    Features:
        - 不强制要求登录
        - 已登录用户更新活动时间
        - 会话超时自动清除
    
    Args:
        f: 被装饰的函数
    
    Returns:
        装饰后的函数
    
    Example:
        @app.route('/api/public/videos')
        @optional_auth
        def public_videos():
            if session.get('authenticated'):
                # 返回个性化内容
                pass
            else:
                # 返回公开内容
                pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('authenticated', False):
            last_activity = session.get('last_activity')
            if last_activity:
                elapsed = time.time() - last_activity
                if elapsed > INACTIVITY_TIMEOUT:
                    session.clear()
                else:
                    session['last_activity'] = time.time()
                    session.modified = True
        return f(*args, **kwargs)
    return decorated_function
