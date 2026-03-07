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

使用示例：
    from web.core.config import config
    
    # 获取开发环境配置
    dev_config = config['development']
    
    # 在应用中使用
    app.config.from_object(config['production'])

环境变量：
    - SECRET_KEY: 应用密钥（可选，默认自动生成）
    - DATABASE_URL: 数据库URL（可选，默认SQLite）
    - VIDEO_BASE_PATH: 视频路径（可选，默认F:\\666）
    - FLASK_ENV: 环境名称（development/production/testing）
    - INACTIVITY_TIMEOUT: 会话超时时间
    - CACHE_CLEANUP_INTERVAL: 缓存清理间隔
"""
import os
import secrets
from datetime import timedelta


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
        INACTIVITY_TIMEOUT: 会话不活动超时时间（秒）
        CACHE_CLEANUP_INTERVAL: 缓存清理间隔（秒）
        AUTH_CONFIG_FILE: 认证配置文件名
        MAX_CONTENT_LENGTH: 最大请求内容长度（10GB）
        JSON_AS_ASCII: JSON是否使用ASCII编码
        JSON_SORT_KEYS: JSON是否排序键
    """
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///./video_library.db'
    DATABASE_ECHO = False
    
    VIDEO_BASE_PATH = os.environ.get('VIDEO_BASE_PATH') or 'F:\\666'
    
    INACTIVITY_TIMEOUT = int(os.environ.get('INACTIVITY_TIMEOUT', 1800))
    CACHE_CLEANUP_INTERVAL = int(os.environ.get('CACHE_CLEANUP_INTERVAL', 300))
    
    AUTH_CONFIG_FILE = '.auth_config.json'
    
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024 * 1024
    
    JSON_AS_ASCII = False
    JSON_SORT_KEYS = False
    
    @classmethod
    def init_app(cls, app):
        """
        初始化应用
        
        子类可覆盖此方法添加额外的初始化逻辑。
        
        Args:
            app: Flask应用实例
        """
        pass


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
    
    @classmethod
    def init_app(cls, app):
        """
        初始化生产环境应用
        
        配置文件日志记录器。
        
        Args:
            app: Flask应用实例
        """
        Config.init_app(app)
        
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/web_app.log',
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Web应用启动')


class TestingConfig(Config):
    """
    测试环境配置
    
    使用内存数据库进行测试。
    
    Attributes:
        TESTING: 启用测试模式
        DATABASE_URL: 使用内存SQLite数据库
    """
    
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
