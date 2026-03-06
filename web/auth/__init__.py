"""
认证模块
"""
from web.auth.service import AuthService, hash_password, verify_password, init_default_password
from web.auth.decorators import login_required, api_login_required, optional_auth
from web.auth.routes import auth_bp, init_auth

__all__ = [
    'AuthService',
    'hash_password',
    'verify_password',
    'init_default_password',
    'login_required',
    'api_login_required',
    'optional_auth',
    'auth_bp',
    'init_auth'
]
