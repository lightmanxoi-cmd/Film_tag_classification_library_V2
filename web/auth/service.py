"""
认证服务 - 密码处理和认证逻辑
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
    """获取认证配置文件路径"""
    if base_dir:
        return os.path.join(base_dir, AUTH_CONFIG_FILE)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), AUTH_CONFIG_FILE)


def load_auth_config(base_dir: str = None) -> dict:
    """加载认证配置"""
    config_path = get_auth_config_path(base_dir)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_auth_config(config: dict, base_dir: str = None):
    """保存认证配置"""
    config_path = get_auth_config_path(base_dir)
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存认证配置失败: {e}")
        return False


def hash_password(password: str) -> str:
    """哈希密码"""
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
    """验证密码"""
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
    返回: (config, is_new) - 配置字典和是否是新创建的
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
    返回: (success, message)
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
    """认证服务类"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir
        self._config = None
    
    @property
    def config(self) -> dict:
        if self._config is None:
            self._config = load_auth_config(self.base_dir)
        return self._config
    
    def reload_config(self):
        """重新加载配置"""
        self._config = load_auth_config(self.base_dir)
    
    def verify(self, password: str) -> bool:
        """验证密码"""
        stored_hash = self.config.get('password_hash', '')
        return verify_password(password, stored_hash)
    
    def change_password(self, old_password: str, new_password: str) -> Tuple[bool, str]:
        """修改密码"""
        result = change_password(old_password, new_password, self.base_dir)
        if result[0]:
            self.reload_config()
        return result
    
    def get_session_secret(self) -> Optional[str]:
        """获取会话密钥"""
        return self.config.get('session_secret')
