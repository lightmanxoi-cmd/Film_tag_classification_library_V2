"""
Flask应用配置模块

提供不同环境的配置类，支持开发、生产、测试环境。

配置类：
    - Config: 基础配置类
    - DevelopmentConfig: 开发环境配置
    - ProductionConfig: 生产环境配置
    - TestingConfig: 测试环境配置

配置项说明：
    - SECRET_KEY: 应用密钥，用于会话签名
    - DATABASE_URL: 数据库连接URL
    - VIDEO_BASE_PATH: 视频文件基础路径
    - INACTIVITY_TIMEOUT: 会话超时时间（秒）
    - MAX_CONTENT_LENGTH: 最大上传文件大小
    - DEFAULT_PASSWORD: 初始默认密码

使用示例：
    from web.core.config import config
    
    # 获取开发环境配置
    dev_config = config['development']
    
    # 在应用中使用
    app.config.from_object(config['production'])

环境变量：
    - SECRET_KEY: 应用密钥（生产环境必须设置）
    - DATABASE_URL: 数据库URL（可选，默认SQLite）
    - VIDEO_BASE_PATH: 视频路径（必须设置）
    - FLASK_ENV: 环境名称（development/production/testing）
    - INACTIVITY_TIMEOUT: 会话超时时间
    - CACHE_CLEANUP_INTERVAL: 缓存清理间隔
    - DEFAULT_PASSWORD: 初始默认密码（可选，首次运行时设置）

安全建议：
    - 生产环境必须设置 SECRET_KEY 环境变量
    - 生产环境必须设置 VIDEO_BASE_PATH 环境变量
    - 生产环境建议设置 DEFAULT_PASSWORD 或在首次运行后立即修改密码
"""
import os
import secrets
import warnings
from datetime import timedelta
from typing import Optional


def _get_video_base_path() -> Optional[str]:
    """
    获取视频基础路径
    
    优先从环境变量读取，如果未设置则返回 None 并发出警告。
    
    Returns:
        Optional[str]: 视频路径或 None
    """
    video_path = os.environ.get('VIDEO_BASE_PATH')
    
    if video_path:
        return video_path
    
    warnings.warn(
        "VIDEO_BASE_PATH 环境变量未设置。"
        "请创建 .env 文件或设置环境变量来配置视频文件路径。"
        "示例: VIDEO_BASE_PATH=/path/to/videos",
        UserWarning,
        stacklevel=3
    )
    
    return None


def _get_secret_key() -> str:
    """
    获取应用密钥
    
    优先从环境变量读取，如果未设置则自动生成（仅适用于开发环境）。
    
    Returns:
        str: 应用密钥
    """
    secret_key = os.environ.get('SECRET_KEY')
    
    if secret_key:
        return secret_key
    
    warnings.warn(
        "SECRET_KEY 环境变量未设置，已自动生成临时密钥。"
        "生产环境请务必设置 SECRET_KEY 环境变量！",
        UserWarning,
        stacklevel=3
    )
    
    return secrets.token_hex(32)


def _get_default_password() -> Optional[str]:
    """
    获取默认密码
    
    从环境变量读取默认密码，如果未设置则返回 None。
    首次运行时如果没有设置，系统会提示用户设置密码。
    
    Returns:
        Optional[str]: 默认密码或 None
    """
    return os.environ.get('DEFAULT_PASSWORD')


class Config:
    """
    基础配置类
    
    包含所有环境共用的配置项。
    
    Attributes:
        SECRET_KEY: 应用密钥，用于会话签名和CSRF保护
        SESSION_COOKIE_SECURE: 是否只在HTTPS下发送Cookie
        SESSION_COOKIE_HTTPONLY: 是否禁止JavaScript访问Cookie
        SESSION_COOKIE_SAMESITE: Cookie同源策略
        PERMANENT_SESSION_LIFETIME: 持久会话有效期
        DATABASE_URL: 数据库连接URL
        DATABASE_ECHO: 是否打印SQL语句
        VIDEO_BASE_PATH: 视频文件存储路径
        CACHE_CLEANUP_INTERVAL: 缓存清理间隔（秒）
        AUTH_CONFIG_FILE: 认证配置文件名
        MAX_CONTENT_LENGTH: 最大请求内容长度（10GB）
        JSON_AS_ASCII: JSON是否使用ASCII编码
        JSON_SORT_KEYS: JSON是否排序键
        DEFAULT_PASSWORD: 初始默认密码
    """
    
    SECRET_KEY = _get_secret_key()
    
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=365)
    
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///./video_library.db'
    DATABASE_ECHO = False
    
    VIDEO_BASE_PATH = _get_video_base_path()
    
    CACHE_CLEANUP_INTERVAL = int(os.environ.get('CACHE_CLEANUP_INTERVAL', '300'))
    
    AUTH_CONFIG_FILE = '.auth_config.json'
    
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024 * 1024
    
    JSON_AS_ASCII = False
    JSON_SORT_KEYS = False
    
    DEFAULT_PASSWORD = _get_default_password()
    
    VIDEO_STREAM_CHUNK_SIZE = int(os.environ.get('VIDEO_STREAM_CHUNK_SIZE', 1024 * 1024))
    VIDEO_CACHE_MAX_AGE = int(os.environ.get('VIDEO_CACHE_MAX_AGE', 3600))
    VIDEO_STREAM_BUFFER_SIZE = int(os.environ.get('VIDEO_STREAM_BUFFER_SIZE', 64 * 1024))
    VIDEO_STREAM_LOG_ENABLED = os.environ.get('VIDEO_STREAM_LOG_ENABLED', 'true').lower() == 'true'
    VIDEO_STREAM_MAX_BANDWIDTH = int(os.environ.get('VIDEO_STREAM_MAX_BANDWIDTH', 0))
    
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-Requested-With']
    CORS_MAX_AGE = int(os.environ.get('CORS_MAX_AGE', '600'))
    
    @classmethod
    def init_app(cls, app):
        """
        初始化应用
        
        子类可覆盖此方法添加额外的初始化逻辑。
        
        Args:
            app: Flask应用实例
        """
        pass
    
    @classmethod
    def validate(cls) -> tuple:
        """
        验证配置
        
        Returns:
            tuple: (是否有效, 错误列表, 警告列表)
        """
        from web.core.config_validator import validate_config
        result = validate_config({
            'SECRET_KEY': cls.SECRET_KEY,
            'DATABASE_URL': cls.DATABASE_URL,
            'VIDEO_BASE_PATH': cls.VIDEO_BASE_PATH,
            'AUTH_CONFIG_FILE': cls.AUTH_CONFIG_FILE,
        })
        return result.is_valid, result.errors, result.warnings


class DevelopmentConfig(Config):
    """
    开发环境配置
    
    启用调试模式和SQL日志输出。
    
    Attributes:
        DEBUG: 启用调试模式
        DATABASE_ECHO: 打印SQL语句
    """
    
    DEBUG = True
    DATABASE_ECHO = True


class ProductionConfig(Config):
    """
    生产环境配置
    
    启用安全配置和日志记录。
    
    Attributes:
        DEBUG: 禁用调试模式
        SESSION_COOKIE_SECURE: 启用安全Cookie（需要HTTPS）
    
    Features:
        - 文件日志记录
        - 日志轮转（10MB，10个备份）
        - 安全会话Cookie
    """
    
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '')
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE']
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization']
    
    @classmethod
    def init_app(cls, app):
        """
        初始化生产环境应用
        
        配置文件日志记录器。
        
        Args:
            app: Flask应用实例
        """
        Config.init_app(app)
        
        from video_tag_system.utils.logger import setup_logging, get_logger
        
        setup_logging(
            level='INFO',
            log_dir='logs',
            json_format=False,
            max_size=10,
            backup_count=10,
            console_output=True,
            console_level='WARNING'
        )
        
        logger = get_logger('web.app')
        logger.info('Web应用启动')


class TestingConfig(Config):
    """
    测试环境配置
    
    使用内存数据库进行测试。
    
    Attributes:
        TESTING: 启用测试模式
        DATABASE_URL: 使用内存SQLite数据库
        VIDEO_BASE_PATH: 测试用临时目录
    """
    
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'
    VIDEO_BASE_PATH = None


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
