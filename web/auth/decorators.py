"""
认证装饰器
"""
import time
from functools import wraps
from flask import request, jsonify, redirect, url_for, session, g

INACTIVITY_TIMEOUT = 1800


def login_required(f):
    """
    登录验证装饰器
    - 检查session中的认证状态
    - 检查会话超时
    - 更新最后活动时间
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
    只返回JSON响应，不重定向
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
    如果已登录则更新活动时间，未登录也允许访问
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
