"""
认证路由蓝图
"""
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, session

from web.auth.service import AuthService, init_default_password
from web.auth.decorators import login_required
from web.core.responses import APIResponse

auth_bp = Blueprint('auth', __name__)

auth_service = AuthService()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面和登录处理"""
    if session.get('authenticated', False):
        return redirect(url_for('pages.index'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        
        if auth_service.verify(password):
            session['authenticated'] = True
            session['last_activity'] = __import__('time').time()
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
    """登出"""
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/v1/change-password', methods=['POST'])
@login_required
def change_password():
    """修改密码API"""
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    success, message = auth_service.change_password(old_password, new_password)
    
    if success:
        return APIResponse.success(message=message)
    else:
        return APIResponse.error(message=message)


def init_auth(app):
    """初始化认证模块"""
    config, is_new = init_default_password(app.root_path)
    
    if config.get('session_secret'):
        app.secret_key = config['session_secret']
    
    if is_new:
        print("=" * 50)
        print("安全登录系统已启用")
        print("初始密码: 13245768")
        print("请登录后及时修改密码！")
        print("=" * 50)
    
    return config
