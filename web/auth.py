"""
安全认证模块 - 使用Argon2id密码哈希算法
Argon2是2015年密码哈希竞赛的获胜者，是目前最安全的密码哈希算法
"""
import os
import json
import secrets
from typing import Optional, Tuple
from functools import wraps
from flask import session, redirect, url_for, request

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, VerificationError
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False
    import hashlib
    import hmac

AUTH_CONFIG_FILE = '.auth_config.json'

class AuthConfig:
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(config_dir, AUTH_CONFIG_FILE)
        self._ensure_config_exists()
    
    def _ensure_config_exists(self):
        if not os.path.exists(self.config_path):
            default_config = {
                'password_hash': '',
                'session_secret': secrets.token_hex(32),
                'max_attempts': 5,
                'lockout_duration': 300,
                'created_at': None
            }
            self._save_config(default_config)
    
    def _load_config(self) -> dict:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {
                'password_hash': '',
                'session_secret': secrets.token_hex(32),
                'max_attempts': 5,
                'lockout_duration': 300,
                'created_at': None
            }
    
    def _save_config(self, config: dict):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def get_session_secret(self) -> str:
        config = self._load_config()
        return config.get('session_secret', secrets.token_hex(32))
    
    def set_password_hash(self, password_hash: str):
        config = self._load_config()
        config['password_hash'] = password_hash
        config['created_at'] = self._get_timestamp()
        self._save_config(config)
    
    def get_password_hash(self) -> str:
        config = self._load_config()
        return config.get('password_hash', '')
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()


class Argon2PasswordHasher:
    def __init__(self):
        if ARGON2_AVAILABLE:
            self.ph = PasswordHasher(
                time_cost=3,
                memory_cost=65536,
                parallelism=4,
                hash_len=32,
                salt_len=16
            )
        else:
            self.ph = None
    
    def hash_password(self, password: str) -> str:
        if ARGON2_AVAILABLE:
            return self.ph.hash(password)
        else:
            salt = os.urandom(32)
            iterations = 100000
            hash_bytes = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                iterations
            )
            return f"pbkdf2_sha256${iterations}${salt.hex()}${hash_bytes.hex()}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        if not password_hash:
            return False
        
        if ARGON2_AVAILABLE:
            try:
                self.ph.verify(password_hash, password)
                return True
            except (VerifyMismatchError, VerificationError):
                return False
        else:
            try:
                parts = password_hash.split('$')
                if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
                    return False
                iterations = int(parts[1])
                salt = bytes.fromhex(parts[2])
                stored_hash = parts[3]
                computed_hash = hashlib.pbkdf2_hmac(
                    'sha256',
                    password.encode('utf-8'),
                    salt,
                    iterations
                ).hex()
                return hmac.compare_digest(stored_hash, computed_hash)
            except Exception:
                return False


class AuthManager:
    def __init__(self, config_dir: str = None):
        self.config = AuthConfig(config_dir)
        self.hasher = Argon2PasswordHasher()
        self._init_default_password()
    
    def _init_default_password(self):
        if not self.config.get_password_hash():
            self.set_password('13245768')
    
    def set_password(self, password: str) -> bool:
        try:
            password_hash = self.hasher.hash_password(password)
            self.config.set_password_hash(password_hash)
            return True
        except Exception as e:
            print(f"设置密码失败: {e}")
            return False
    
    def verify_password(self, password: str) -> bool:
        stored_hash = self.config.get_password_hash()
        return self.hasher.verify_password(password, stored_hash)
    
    def get_session_secret(self) -> str:
        return self.config.get_session_secret()
    
    def login(self, password: str) -> Tuple[bool, str]:
        if self.verify_password(password):
            session['authenticated'] = True
            session.permanent = True
            return True, "登录成功"
        return False, "密码错误"
    
    def logout(self):
        session.clear()
    
    def is_authenticated(self) -> bool:
        return session.get('authenticated', False)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated', False):
            if request.path.startswith('/api/') or request.path.startswith('/video/'):
                return {'success': False, 'error': '未授权访问，请先登录'}, 401
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


auth_manager = None

def init_auth(app, config_dir: str = None):
    global auth_manager
    auth_manager = AuthManager(config_dir)
    app.secret_key = auth_manager.get_session_secret()
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400
    return auth_manager

def get_auth_manager() -> AuthManager:
    global auth_manager
    if auth_manager is None:
        raise RuntimeError("认证管理器未初始化，请先调用 init_auth()")
    return auth_manager
