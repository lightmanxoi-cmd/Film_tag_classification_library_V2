"""
认证服务模块

提供密码处理和认证逻辑，支持Argon2和PBKDF2两种哈希算法。

主要功能：
    - hash_password: 密码哈希
    - verify_password: 密码验证
    - init_default_password: 初始化默认密码
    - change_password: 修改密码
    - AuthService: 认证服务类

密码算法：
    首选：Argon2（推荐，需要安装argon2-cffi）
    后备：PBKDF2-SHA256（Python内置）

Argon2参数：
    - time_cost: 3（迭代次数）
    - memory_cost: 65536 KB（内存使用）
    - parallelism: 4（并行线程数）
    - hash_len: 32（哈希长度）
    - salt_len: 16（盐值长度）

PBKDF2参数：
    - iterations: 100000（迭代次数）
    - hash: SHA256

配置文件：
    .auth_config.json - 存储密码哈希和会话密钥

使用示例：
    from web.auth.service import AuthService
    
    auth = AuthService()
    
    # 验证密码
    if auth.verify(password):
        print("登录成功")
    
    # 修改密码
    success, message = auth.change_password(old, new)

安全建议：
    - 安装argon2-cffi以获得更好的安全性
    - 定期更换密码
    - 使用强密码（至少8位，包含大小写字母和数字）
"""
import os
import json
import hashlib
import hmac
import secrets
from typing import Tuple, Optional

AUTH_CONFIG_FILE = '.auth_config.json'

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, VerificationError
    ARGON2_AVAILABLE = True
    ph = PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16
    )
except ImportError:
    ARGON2_AVAILABLE = False
    ph = None
    print("警告: argon2-cffi 未安装，将使用 PBKDF2-SHA256 作为后备方案")
    print("建议运行: pip install argon2-cffi")


def get_auth_config_path(base_dir: str = None) -> str:
    """
    获取认证配置文件路径
    
    Args:
        base_dir: 基础目录，默认为web模块的上级目录
    
    Returns:
        str: 配置文件的绝对路径
    
    Example:
        path = get_auth_config_path('/app')
        # 返回: /app/.auth_config.json
    """
    if base_dir:
        return os.path.join(base_dir, AUTH_CONFIG_FILE)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), AUTH_CONFIG_FILE)


def load_auth_config(base_dir: str = None) -> dict:
    """
    加载认证配置
    
    从配置文件加载认证配置，如果文件不存在则返回空字典。
    
    Args:
        base_dir: 基础目录
    
    Returns:
        dict: 认证配置字典
    
    Example:
        config = load_auth_config()
        password_hash = config.get('password_hash')
    """
    config_path = get_auth_config_path(base_dir)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_auth_config(config: dict, base_dir: str = None):
    """
    保存认证配置
    
    将认证配置保存到文件。
    
    Args:
        config: 配置字典
        base_dir: 基础目录
    
    Returns:
        bool: 保存是否成功
    
    Example:
        save_auth_config({'password_hash': '...'})
    """
    config_path = get_auth_config_path(base_dir)
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存认证配置失败: {e}")
        return False


def hash_password(password: str) -> str:
    """
    哈希密码
    
    使用Argon2或PBKDF2-SHA256对密码进行哈希。
    Argon2是首选算法，如果不可用则使用PBKDF2。
    
    Args:
        password: 明文密码
    
    Returns:
        str: 哈希后的密码字符串
    
    Example:
        hashed = hash_password('mypassword')
        # Argon2: $argon2id$v=19$m=65536,t=3,p=4$...
        # PBKDF2: pbkdf2_sha256$100000$...$...
    """
    if ARGON2_AVAILABLE:
        return ph.hash(password)
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


def verify_password(password: str, password_hash: str) -> bool:
    """
    验证密码
    
    验证明文密码是否与哈希值匹配。
    自动识别Argon2和PBKDF2格式。
    
    Args:
        password: 明文密码
        password_hash: 存储的密码哈希
    
    Returns:
        bool: 密码是否匹配
    
    Example:
        if verify_password('mypassword', stored_hash):
            print("密码正确")
    """
    if not password_hash:
        return False
    
    if ARGON2_AVAILABLE:
        try:
            ph.verify(password_hash, password)
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


def init_default_password(base_dir: str = None, default_password: str = '13245768') -> Tuple[dict, bool]:
    """
    初始化默认密码
    
    如果配置文件中不存在密码哈希，则创建默认密码。
    
    Args:
        base_dir: 基础目录
        default_password: 默认密码，默认'13245768'
    
    Returns:
        Tuple[dict, bool]: (配置字典, 是否是新创建的)
    
    Side Effects:
        - 创建或更新.auth_config.json文件
        - 生成会话密钥
    
    Example:
        config, is_new = init_default_password()
        if is_new:
            print("请使用默认密码登录后修改密码")
    """
    config = load_auth_config(base_dir)
    is_new = False
    
    if not config.get('password_hash'):
        password_hash = hash_password(default_password)
        config['password_hash'] = password_hash
        config['session_secret'] = secrets.token_hex(32)
        save_auth_config(config, base_dir)
        is_new = True
        print(f"已设置默认密码: {default_password}")
        print("请登录后及时修改密码！")
    
    return config, is_new


def change_password(old_password: str, new_password: str, base_dir: str = None) -> Tuple[bool, str]:
    """
    修改密码
    
    验证原密码并设置新密码。
    
    Args:
        old_password: 原密码
        new_password: 新密码
        base_dir: 基础目录
    
    Returns:
        Tuple[bool, str]: (是否成功, 消息)
    
    Validation:
        - 原密码和新密码不能为空
        - 新密码长度至少6位
        - 原密码必须正确
    
    Example:
        success, message = change_password('oldpass', 'newpass')
        if success:
            print("密码修改成功")
    """
    if not old_password or not new_password:
        return False, '请填写完整信息'
    
    if len(new_password) < 6:
        return False, '新密码长度至少6位'
    
    config = load_auth_config(base_dir)
    stored_hash = config.get('password_hash', '')
    
    if not verify_password(old_password, stored_hash):
        return False, '原密码错误'
    
    new_hash = hash_password(new_password)
    config['password_hash'] = new_hash
    save_auth_config(config, base_dir)
    
    return True, '密码修改成功'


class AuthService:
    """
    认证服务类
    
    封装认证相关操作，提供统一的接口。
    
    Attributes:
        base_dir: 基础目录
        _config: 缓存的配置字典
    
    Methods:
        verify: 验证密码
        change_password: 修改密码
        get_session_secret: 获取会话密钥
        reload_config: 重新加载配置
    
    Example:
        auth = AuthService('/app')
        
        if auth.verify('password'):
            session['authenticated'] = True
    """
    
    def __init__(self, base_dir: str = None):
        """
        初始化认证服务
        
        Args:
            base_dir: 基础目录，用于定位配置文件
        """
        self.base_dir = base_dir
        self._config = None
    
    @property
    def config(self) -> dict:
        """
        获取配置（懒加载）
        
        Returns:
            dict: 认证配置字典
        """
        if self._config is None:
            self._config = load_auth_config(self.base_dir)
        return self._config
    
    def reload_config(self):
        """
        重新加载配置
        
        清除缓存并重新从文件加载配置。
        通常在修改密码后调用。
        """
        self._config = load_auth_config(self.base_dir)
    
    def verify(self, password: str) -> bool:
        """
        验证密码
        
        Args:
            password: 明文密码
        
        Returns:
            bool: 密码是否正确
        
        Example:
            if auth.verify('mypassword'):
                print("验证通过")
        """
        stored_hash = self.config.get('password_hash', '')
        return verify_password(password, stored_hash)
    
    def change_password(self, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        修改密码
        
        Args:
            old_password: 原密码
            new_password: 新密码
        
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        
        Example:
            success, msg = auth.change_password('old', 'newpass')
        """
        result = change_password(old_password, new_password, self.base_dir)
        if result[0]:
            self.reload_config()
        return result
    
    def get_session_secret(self) -> Optional[str]:
        """
        获取会话密钥
        
        Returns:
            Optional[str]: 会话密钥，不存在则返回None
        
        Example:
            secret = auth.get_session_secret()
            if secret:
                app.secret_key = secret
        """
        return self.config.get('session_secret')
