"""
Flask应用配置
"""
import os
import secrets
from datetime import timedelta


class Config:
    """基础配置"""
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


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    DATABASE_ECHO = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    @classmethod
    def init_app(cls, app):
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
    """测试环境配置"""
    TESTING = True
    DATABASE_URL = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
