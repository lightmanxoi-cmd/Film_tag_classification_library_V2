"""
安全认证模块 - 使用Argon2id密码哈希算法

Argon2是2015年密码哈希竞赛的获胜者，是目前最安全的密码哈希算法。
本模块提供完整的认证管理功能，包括密码哈希、会话管理、登录验证等。

主要组件：
    - AuthConfig: 认证配置管理类
    - Argon2PasswordHasher: Argon2密码哈希类
    - AuthManager: 认证管理器类
    - login_required: 登录验证装饰器
    - init_auth: 初始化认证模块
    - get_auth_manager: 获取认证管理器实例

密码算法：
    首选：Argon2id（推荐，需要安装argon2-cffi）
    后备：PBKDF2-SHA256（Python内置）

Argon2参数：
    - time_cost: 3（迭代次数）
    - memory_cost: 65536 KB（内存使用）
    - parallelism: 4（并行线程数）
    - hash_len: 32（哈希长度）
    - salt_len: 16（盐值长度）

使用示例：
    from web.auth import init_auth, login_required
    
    # 初始化认证
    auth = init_auth(app)
    
    # 使用装饰器保护路由
    @app.route('/protected')
    @login_required
    def protected():
        return "已登录用户可见"

配置文件：
    .auth_config.json - 存储密码哈希和会话密钥

安全特性：
    - Argon2id密码哈希（抗GPU/ASIC攻击）
    - 随机盐值
    - 会话密钥自动生成
    - 安全Cookie设置

初始密码：
    首次运行时自动设置默认密码：13245768
    请登录后及时修改密码！
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
    """
    认证配置管理类
    
    管理认证配置文件的读取和写入。
    配置文件存储密码哈希、会话密钥等信息。
    
    Attributes:
        config_path: 配置文件路径
    
    Config Structure:
        {
            "password_hash": "哈希后的密码",
            "session_secret": "会话密钥",
            "max_attempts": 5,
            "lockout_duration": 300,
            "created_at": "创建时间"
        }
    """
    
    def __init__(self, config_dir: str = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录，默认为项目根目录
        """
        if config_dir is None:
            config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(config_dir, AUTH_CONFIG_FILE)
        self._ensure_config_exists()
    
    def _ensure_config_exists(self):
        """确保配置文件存在，不存在则创建默认配置"""
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
        """
        加载配置
        
        Returns:
            dict: 配置字典
        """
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
        """
        保存配置
        
        Args:
            config: 配置字典
        """
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def get_session_secret(self) -> str:
        """
        获取会话密钥
        
        Returns:
            str: 会话密钥
        """
        config = self._load_config()
        return config.get('session_secret', secrets.token_hex(32))
    
    def set_password_hash(self, password_hash: str):
        """
        设置密码哈希
        
        Args:
            password_hash: 哈希后的密码
        """
        config = self._load_config()
        config['password_hash'] = password_hash
        config['created_at'] = self._get_timestamp()
        self._save_config(config)
    
    def get_password_hash(self) -> str:
        """
        获取密码哈希
        
        Returns:
            str: 存储的密码哈希
        """
        config = self._load_config()
        return config.get('password_hash', '')
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


class Argon2PasswordHasher:
    """
    Argon2密码哈希类
    
    提供密码哈希和验证功能。
    优先使用Argon2id算法，不可用时降级到PBKDF2-SHA256。
    
    Argon2id是Argon2的混合变体，结合了Argon2i和Argon2d的优点：
    - 抗GPU攻击
    - 抗侧信道攻击
    - 抗时间-空间权衡攻击
    """
    
    def __init__(self):
        """初始化密码哈希器"""
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
        """
        哈希密码
        
        Args:
            password: 明文密码
        
        Returns:
            str: 哈希后的密码字符串
        
        Example:
            hasher = Argon2PasswordHasher()
            hashed = hasher.hash_password('mypassword')
        """
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
        """
        验证密码
        
        Args:
            password: 明文密码
            password_hash: 存储的密码哈希
        
        Returns:
            bool: 密码是否匹配
        
        Example:
            if hasher.verify_password('mypassword', stored_hash):
                print("密码正确")
        """
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
    """
    认证管理器类
    
    提供完整的认证功能，包括密码设置、验证、登录登出等。
    
    Attributes:
        config: AuthConfig实例
        hasher: Argon2PasswordHasher实例
    
    Methods:
        set_password: 设置密码
        verify_password: 验证密码
        login: 登录
        logout: 登出
        is_authenticated: 检查是否已登录
    
    Example:
        auth = AuthManager()
        
        # 设置密码
        auth.set_password('newpassword')
        
        # 验证登录
        success, message = auth.login('password')
    """
    
    def __init__(self, config_dir: str = None):
        """
        初始化认证管理器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config = AuthConfig(config_dir)
        self.hasher = Argon2PasswordHasher()
        self._init_default_password()
    
    def _init_default_password(self):
        """初始化默认密码，如果不存在则设置"""
        if not self.config.get_password_hash():
            self.set_password('13245768')
    
    def set_password(self, password: str) -> bool:
        """
        设置密码
        
        Args:
            password: 新密码
        
        Returns:
            bool: 设置是否成功
        """
        try:
            password_hash = self.hasher.hash_password(password)
            self.config.set_password_hash(password_hash)
            return True
        except Exception as e:
            print(f"设置密码失败: {e}")
            return False
    
    def verify_password(self, password: str) -> bool:
        """
        验证密码
        
        Args:
            password: 待验证的密码
        
        Returns:
            bool: 密码是否正确
        """
        stored_hash = self.config.get_password_hash()
        return self.hasher.verify_password(password, stored_hash)
    
    def get_session_secret(self) -> str:
        """
        获取会话密钥
        
        Returns:
            str: 会话密钥
        """
        return self.config.get_session_secret()
    
    def login(self, password: str) -> Tuple[bool, str]:
        """
        登录
        
        验证密码并设置会话状态。
        
        Args:
            password: 密码
        
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        if self.verify_password(password):
            session['authenticated'] = True
            session.permanent = True
            return True, "登录成功"
        return False, "密码错误"
    
    def logout(self):
        """登出，清除会话"""
        session.clear()
    
    def is_authenticated(self) -> bool:
        """
        检查是否已登录
        
        Returns:
            bool: 是否已登录
        """
        return session.get('authenticated', False)


def login_required(f):
    """
    登录验证装饰器
    
    验证用户是否已登录，未登录则返回错误或重定向。
    - API请求：返回401 JSON错误
    - 页面请求：重定向到登录页
    
    Args:
        f: 被装饰的函数
    
    Returns:
        装饰后的函数
    
    Example:
        @app.route('/protected')
        @login_required
        def protected():
            return "已登录用户可见"
    """
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
    """
    初始化认证模块
    
    创建认证管理器并配置Flask应用的会话设置。
    
    Args:
        app: Flask应用实例
        config_dir: 配置文件目录
    
    Returns:
        AuthManager: 认证管理器实例
    
    Side Effects:
        - 设置app.secret_key
        - 配置会话Cookie设置
    
    Example:
        auth = init_auth(app)
    """
    global auth_manager
    auth_manager = AuthManager(config_dir)
    app.secret_key = auth_manager.get_session_secret()
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400
    return auth_manager


def get_auth_manager() -> AuthManager:
    """
    获取认证管理器实例
    
    Returns:
        AuthManager: 认证管理器实例
    
    Raises:
        RuntimeError: 如果认证管理器未初始化
    
    Example:
        auth = get_auth_manager()
        if auth.verify_password('password'):
            print("验证通过")
    """
    global auth_manager
    if auth_manager is None:
        raise RuntimeError("认证管理器未初始化，请先调用 init_auth()")
    return auth_manager
