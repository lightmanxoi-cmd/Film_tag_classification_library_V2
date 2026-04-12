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
    .auth_config.json - 仅存储密码哈希

会话密钥：
    从环境变量 SESSION_SECRET 或 SECRET_KEY 读取，不再存储到配置文件中。
    如果两者均未设置，则自动生成临时密钥（仅适用于开发环境）。

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
    - 生产环境必须设置 SESSION_SECRET 或 SECRET_KEY 环境变量
"""
import os
import json
import hashlib
import hmac
import secrets
from typing import Tuple, Optional

from video_tag_system.utils.logger import get_logger, console

logger = get_logger(__name__)

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
    logger.warning("argon2-cffi 未安装，将使用 PBKDF2-SHA256 作为后备方案")
    logger.info("建议运行: pip install argon2-cffi")


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
        logger.error(f"保存认证配置失败: {e}")
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


def get_session_secret() -> str:
    """
    获取会话密钥
    
    从环境变量读取会话密钥，优先级：
    1. SESSION_SECRET 环境变量（推荐）
    2. SECRET_KEY 环境变量（兼容）
    3. 自动生成临时密钥（仅开发环境）
    
    Returns:
        str: 会话密钥
    
    Example:
        secret = get_session_secret()
        app.secret_key = secret
    
    Security:
        - 生产环境必须设置 SESSION_SECRET 或 SECRET_KEY 环境变量
        - 自动生成的密钥在服务重启后会变化，导致会话失效
    """
    session_secret = os.environ.get('SESSION_SECRET')
    if session_secret:
        return session_secret
    
    secret_key = os.environ.get('SECRET_KEY')
    if secret_key:
        return secret_key
    
    logger.warning(
        "SESSION_SECRET 和 SECRET_KEY 环境变量均未设置，已自动生成临时密钥。"
        "生产环境请务必设置 SESSION_SECRET 环境变量！"
    )
    return secrets.token_hex(32)


def init_default_password(base_dir: str = None, default_password: str = None) -> Tuple[dict, bool]:
    """
    初始化默认密码
    
    如果配置文件中不存在密码哈希，则创建默认密码。
    默认密码优先从环境变量 DEFAULT_PASSWORD 读取，如果未设置则提示用户设置。
    
    注意：会话密钥不再存储到配置文件中，而是从环境变量 SESSION_SECRET/SECRET_KEY 读取。
    
    Args:
        base_dir: 基础目录
        default_password: 默认密码，如果为None则从环境变量读取
    
    Returns:
        Tuple[dict, bool]: (配置字典, 是否是新创建的)
    
    Side Effects:
        - 创建或更新.auth_config.json文件（仅存储密码哈希）
    
    Environment Variables:
        DEFAULT_PASSWORD: 默认密码（推荐设置）
        SESSION_SECRET: 会话密钥（推荐设置）
        SECRET_KEY: 应用密钥（兼容，SESSION_SECRET 优先）
    
    Example:
        config, is_new = init_default_password()
        if is_new:
            print("请使用默认密码登录后修改密码")
    
    Security:
        - 生产环境强烈建议设置 DEFAULT_PASSWORD 环境变量
        - 首次运行后请立即修改密码
        - 生产环境必须设置 SESSION_SECRET 或 SECRET_KEY 环境变量
    """
    config = load_auth_config(base_dir)
    is_new = False
    
    if 'session_secret' in config:
        session_secret_value = config.pop('session_secret')
        save_auth_config(config, base_dir)
        logger.info("已从配置文件中移除session_secret字段，会话密钥已迁移至环境变量SESSION_SECRET")
        if session_secret_value:
            console.separator()
            console.warning("安全迁移提示: 检测到配置文件中存在会话密钥(session_secret)")
            console.info("会话密钥已从配置文件中移除，请将其迁移至环境变量:")
            console.info("  1. 在 .env 文件中添加: SESSION_SECRET=<your-session-secret>")
            console.info("  2. 或设置系统环境变量: set SESSION_SECRET=<your-session-secret>")
            console.info("  注意: 如果不设置SESSION_SECRET，系统将自动生成临时密钥（重启后失效）")
            console.separator()
    
    if not config.get('password_hash'):
        if default_password is None:
            default_password = os.environ.get('DEFAULT_PASSWORD')
        
        if default_password:
            password_hash = hash_password(default_password)
            config['password_hash'] = password_hash
            save_auth_config(config, base_dir)
            is_new = True
            console.separator()
            console.info("安全提示: 已设置初始密码")
            console.separator()
            console.warning("请登录后立即修改密码！")
            console.separator()
            logger.info("已初始化默认密码")
        else:
            console.separator()
            console.warning("警告: 未设置初始密码")
            console.separator()
            console.info("请通过以下方式之一设置密码:")
            console.info("  1. 设置环境变量: DEFAULT_PASSWORD=your_password")
            console.info("  2. 创建 .env 文件并添加: DEFAULT_PASSWORD=your_password")
            console.info("  3. 首次访问时系统会引导您设置密码")
            console.separator()
            config['password_pending'] = True
            save_auth_config(config, base_dir)
            is_new = True
            logger.warning("未设置初始密码，需要手动配置")
    
    has_session_secret = os.environ.get('SESSION_SECRET') or os.environ.get('SECRET_KEY')
    if not has_session_secret:
        console.separator()
        console.warning("安全提示: SESSION_SECRET 环境变量未设置")
        console.info("生产环境请设置 SESSION_SECRET 环境变量以确保会话安全")
        console.info("生成方法: python -c \"import secrets; print(secrets.token_hex(32))\"")
        console.separator()
    
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
    
    logger.info("密码修改成功")
    
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
        result = verify_password(password, stored_hash)
        if result:
            logger.debug("密码验证通过")
        else:
            logger.warning("密码验证失败")
        return result
    
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
    
    def get_session_secret(self) -> str:
        """
        获取会话密钥
        
        从环境变量读取会话密钥，优先级：
        1. SESSION_SECRET 环境变量（推荐）
        2. SECRET_KEY 环境变量（兼容）
        3. 自动生成临时密钥（仅开发环境）
        
        Returns:
            str: 会话密钥
        
        Example:
            secret = auth.get_session_secret()
            app.secret_key = secret
        
        Security:
            - 生产环境必须设置 SESSION_SECRET 或 SECRET_KEY 环境变量
            - 自动生成的密钥在服务重启后会变化，导致会话失效
        """
        return get_session_secret()
