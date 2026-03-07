"""
Web核心模块

提供Flask应用的核心功能，包括配置、响应格式化、错误处理和扩展。

主要组件：
    - Config: 应用配置类
    - config: 配置字典
    - APIResponse: 统一API响应格式
    - ErrorCode: 错误码定义
    - register_error_handlers: 注册错误处理器
    - handle_exceptions: 异常处理装饰器
    - cors: CORS跨域扩展

使用示例：
    from web.core import Config, APIResponse, register_error_handlers
    
    # 使用配置
    app.config.from_object(Config)
    
    # 返回API响应
    return APIResponse.success(data={'key': 'value'})
    
    # 注册错误处理
    register_error_handlers(app)
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
