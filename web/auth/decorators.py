"""
认证装饰器模块

提供登录验证和会话管理的装饰器。

主要功能：
    - login_required: 登录验证装饰器
    - api_login_required: API专用登录验证装饰器
    - optional_auth: 可选认证装饰器

会话管理：
    - 检查session中的认证状态
    - 绝对超时：登录后24小时强制失效（SESSION_ABSOLUTE_TIMEOUT）
    - 空闲超时：无操作2小时后自动失效（INACTIVITY_TIMEOUT）
    - 每次请求更新最后活动时间

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
from flask import request, jsonify, redirect, url_for, session, current_app


def _check_session_timeout():
    """
    检查会话是否超时
    
    验证会话的绝对超时和空闲超时：
    - 绝对超时：从登录时刻起，超过SESSION_ABSOLUTE_TIMEOUT秒后失效
    - 空闲超时：从最后活动时刻起，超过INACTIVITY_TIMEOUT秒后失效
    
    Returns:
        tuple: (is_valid, reason)
            - is_valid: 会话是否有效
            - reason: 失效原因，有效时为None
    
    Side Effects:
        - 超时时会清除会话
    """
    now = time.time()
    
    absolute_timeout = current_app.config.get('SESSION_ABSOLUTE_TIMEOUT', 86400)
    inactivity_timeout = current_app.config.get('INACTIVITY_TIMEOUT', 7200)
    
    login_time = session.get('login_time')
    if login_time is not None:
        if now - login_time > absolute_timeout:
            session.clear()
            return False, 'session_absolute_timeout'
    
    last_activity = session.get('last_activity')
    if last_activity is not None:
        if now - last_activity > inactivity_timeout:
            session.clear()
            return False, 'session_inactivity_timeout'
    
    return True, None


def login_required(f):
    """
    登录验证装饰器
    
    验证用户是否已登录，并检查会话超时：
    - 绝对超时：登录后超过24小时自动失效
    - 空闲超时：无操作超过2小时自动失效
    - Web页面请求：未登录重定向到登录页
    - API请求：返回401 JSON错误
    
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
        
        is_valid, reason = _check_session_timeout()
        if not is_valid:
            if request.path.startswith('/api/') or request.path.startswith('/video/'):
                if reason == 'session_absolute_timeout':
                    error_msg = '会话已过期，请重新登录'
                else:
                    error_msg = '长时间未操作，请重新登录'
                return jsonify({
                    'success': False, 
                    'error': error_msg,
                    'error_code': reason.upper()
                }), 401
            
            from flask import flash
            if reason == 'session_absolute_timeout':
                flash('会话已过期，请重新登录', 'warning')
            else:
                flash('长时间未操作，请重新登录', 'warning')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function


def api_login_required(f):
    """
    API专用登录验证装饰器
    
    与login_required类似，但只返回JSON响应，不进行重定向。
    适用于纯API接口的认证。
    
    Features:
        - 检查session['authenticated']状态
        - 绝对超时和空闲超时检查
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
        
        is_valid, reason = _check_session_timeout()
        if not is_valid:
            if reason == 'session_absolute_timeout':
                error_msg = '会话已过期，请重新登录'
            else:
                error_msg = '长时间未操作，请重新登录'
            return jsonify({
                'success': False, 
                'error': error_msg,
                'error_code': reason.upper()
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function


def optional_auth(f):
    """
    可选认证装饰器
    
    如果用户已登录则允许访问，未登录也允许访问。
    适用于需要区分登录/未登录状态的公开接口。
    不会因超时强制登出，仅检查认证状态。
    
    Args:
        f: 被装饰的函数
    
    Returns:
        装饰后的函数
    
    Example:
        @app.route('/api/public/videos')
        @optional_auth
        def public_videos():
            if session.get('authenticated'):
                pass
            else:
                pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function
