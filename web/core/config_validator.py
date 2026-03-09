"""
配置验证模块

提供配置验证功能，确保应用启动时配置正确。

主要功能：
    - validate_config: 验证配置完整性
    - validate_video_path: 验证视频路径
    - validate_auth_config: 验证认证配置
    - ConfigurationError: 配置错误异常

使用示例：
    from web.core.config_validator import validate_config, ConfigurationError
    
    try:
        validate_config(app.config)
    except ConfigurationError as e:
        print(f"配置错误: {e}")
        sys.exit(1)
"""
import os
import sys
from typing import List, Tuple, Optional
from dataclasses import dataclass


class ConfigurationError(Exception):
    """配置错误异常"""
    
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("\n".join(errors))
    
    def __str__(self):
        return "配置验证失败:\n" + "\n".join(f"  - {e}" for e in self.errors)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


def validate_video_path(video_path: str) -> Tuple[bool, str]:
    """
    验证视频路径配置
    
    Args:
        video_path: 视频文件路径
    
    Returns:
        Tuple[bool, str]: (是否有效, 错误/警告消息)
    """
    if not video_path:
        return False, "VIDEO_BASE_PATH 未配置"
    
    if not os.path.exists(video_path):
        return False, f"视频路径不存在: {video_path}"
    
    if not os.path.isdir(video_path):
        return False, f"视频路径不是目录: {video_path}"
    
    return True, ""


def validate_auth_config(auth_config_path: str = None) -> Tuple[bool, str]:
    """
    验证认证配置
    
    Args:
        auth_config_path: 认证配置文件路径
    
    Returns:
        Tuple[bool, str]: (是否有效, 警告消息)
    """
    import json
    
    if auth_config_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        auth_config_path = os.path.join(base_dir, '.auth_config.json')
    
    if not os.path.exists(auth_config_path):
        return True, "认证配置文件不存在，将在首次运行时创建"
    
    try:
        with open(auth_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if not config.get('password_hash'):
            return True, "密码未设置，首次登录将使用环境变量或需要设置密码"
        
        if not config.get('session_secret'):
            return True, "会话密钥未设置，将自动生成"
        
        return True, ""
    except json.JSONDecodeError:
        return False, f"认证配置文件格式错误: {auth_config_path}"
    except Exception as e:
        return False, f"读取认证配置失败: {e}"


def validate_database_config(database_url: str) -> Tuple[bool, str]:
    """
    验证数据库配置
    
    Args:
        database_url: 数据库连接URL
    
    Returns:
        Tuple[bool, str]: (是否有效, 错误消息)
    """
    if not database_url:
        return False, "DATABASE_URL 未配置"
    
    if database_url.startswith('sqlite:///'):
        db_path = database_url.replace('sqlite:///', '')
        if not os.path.exists(db_path):
            return True, f"数据库文件不存在，将创建: {db_path}"
    
    return True, ""


def validate_config(config: dict, strict: bool = False) -> ValidationResult:
    """
    验证应用配置
    
    Args:
        config: Flask应用配置字典
        strict: 严格模式，警告也视为错误
    
    Returns:
        ValidationResult: 验证结果
    """
    errors = []
    warnings = []
    
    video_path = config.get('VIDEO_BASE_PATH')
    if video_path:
        is_valid, msg = validate_video_path(video_path)
        if not is_valid:
            errors.append(msg)
    else:
        warnings.append("VIDEO_BASE_PATH 未设置，视频功能可能无法正常工作")
    
    database_url = config.get('DATABASE_URL')
    if database_url:
        is_valid, msg = validate_database_config(database_url)
        if not is_valid:
            errors.append(msg)
        elif msg:
            warnings.append(msg)
    else:
        errors.append("DATABASE_URL 未配置")
    
    secret_key = config.get('SECRET_KEY')
    if not secret_key:
        errors.append("SECRET_KEY 未配置")
    elif len(secret_key) < 16:
        warnings.append("SECRET_KEY 长度过短，建议至少16个字符")
    
    auth_config_path = config.get('AUTH_CONFIG_FILE', '.auth_config.json')
    is_valid, msg = validate_auth_config(auth_config_path)
    if not is_valid:
        errors.append(msg)
    elif msg:
        warnings.append(msg)
    
    if strict:
        errors.extend(warnings)
        warnings = []
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )


def check_environment() -> Tuple[bool, List[str], List[str]]:
    """
    检查运行环境
    
    Returns:
        Tuple[bool, List[str], List[str]]: (是否通过, 错误列表, 警告列表)
    """
    errors = []
    warnings = []
    
    video_path = os.environ.get('VIDEO_BASE_PATH')
    if video_path:
        is_valid, msg = validate_video_path(video_path)
        if not is_valid:
            errors.append(msg)
    else:
        warnings.append("VIDEO_BASE_PATH 环境变量未设置，请配置视频文件路径")
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        warnings.append("DATABASE_URL 环境变量未设置，将使用默认 SQLite 数据库")
    
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        warnings.append("SECRET_KEY 环境变量未设置，将自动生成（生产环境建议手动设置）")
    
    default_password = os.environ.get('DEFAULT_PASSWORD')
    if default_password:
        warnings.append("DEFAULT_PASSWORD 环境变量已设置，请确保在生产环境中修改默认密码")
    
    return len(errors) == 0, errors, warnings


def print_config_status():
    """打印配置状态"""
    print("=" * 60)
    print("配置状态检查")
    print("=" * 60)
    
    is_valid, errors, warnings = check_environment()
    
    video_path = os.environ.get('VIDEO_BASE_PATH', '(未设置)')
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///./video_library.db (默认)')
    secret_key = os.environ.get('SECRET_KEY', '(自动生成)')
    
    print(f"  VIDEO_BASE_PATH: {video_path}")
    print(f"  DATABASE_URL: {database_url}")
    print(f"  SECRET_KEY: {'(已设置)' if os.environ.get('SECRET_KEY') else '(自动生成)'}")
    print(f"  DEFAULT_PASSWORD: {'(已设置)' if os.environ.get('DEFAULT_PASSWORD') else '(未设置)'}")
    
    print("-" * 60)
    
    if warnings:
        print("警告:")
        for w in warnings:
            print(f"  ⚠ {w}")
    
    if errors:
        print("错误:")
        for e in errors:
            print(f"  ❌ {e}")
    
    if not warnings and not errors:
        print("✓ 配置检查通过")
    
    print("=" * 60)
    
    return is_valid


def require_config(config: dict):
    """
    要求配置有效，否则退出程序
    
    Args:
        config: Flask应用配置字典
    
    Raises:
        ConfigurationError: 配置无效时抛出
    """
    result = validate_config(config)
    
    if not result.is_valid:
        print("\n" + "=" * 60)
        print("配置验证失败!")
        print("=" * 60)
        for e in result.errors:
            print(f"  ❌ {e}")
        print("\n请检查以下配置:")
        print("  1. 设置 VIDEO_BASE_PATH 环境变量或创建 .env 文件")
        print("  2. 确保 SECRET_KEY 已设置")
        print("  3. 检查数据库配置")
        print("=" * 60)
        raise ConfigurationError(result.errors)
    
    if result.warnings:
        print("\n配置警告:")
        for w in result.warnings:
            print(f"  ⚠ {w}")
