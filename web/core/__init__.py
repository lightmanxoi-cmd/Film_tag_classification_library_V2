"""
Web核心模块
"""
from web.core.config import Config, config
from web.core.responses import APIResponse
from web.core.errors import ErrorCode, register_error_handlers, handle_exceptions
from web.core.extensions import cors

__all__ = [
    'Config',
    'config',
    'APIResponse',
    'ErrorCode',
    'register_error_handlers',
    'handle_exceptions',
    'cors'
]
