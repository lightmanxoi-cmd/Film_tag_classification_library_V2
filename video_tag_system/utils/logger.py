"""
统一日志系统模块

提供结构化日志记录、性能监控和错误追踪功能。

功能特性：
    - 结构化 JSON 格式日志
    - 多处理器支持（控制台、文件、轮转文件）
    - 性能监控装饰器
    - 请求追踪 ID
    - 敏感信息自动过滤

使用示例：
    from video_tag_system.utils.logger import get_logger, setup_logging
    
    # 初始化日志系统
    setup_logging(level='INFO', log_dir='logs')
    
    # 获取模块日志器
    logger = get_logger(__name__)
    
    # 记录日志
    logger.info("应用启动", extra={'version': '1.0.0'})
    logger.error("操作失败", exc_info=True)

配置环境变量：
    - LOG_LEVEL: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - LOG_DIR: 日志文件目录
    - LOG_FORMAT: 日志格式 (text/json)
    - LOG_MAX_SIZE: 单个日志文件最大大小 (MB)
    - LOG_BACKUP_COUNT: 保留的日志文件数量
"""
import os
import sys
import time
import functools
import threading
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from contextvars import ContextVar
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


_request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


SENSITIVE_KEYS = frozenset([
    'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
    'authorization', 'auth', 'credential', 'private_key', 'access_token',
    'refresh_token', 'session_id', 'cookie'
])


def mask_sensitive(data: Any, depth: int = 0) -> Any:
    """
    递归遮蔽敏感信息
    
    Args:
        data: 要处理的数据
        depth: 当前递归深度，防止循环引用
    
    Returns:
        处理后的数据，敏感字段被替换为 '***'
    """
    if depth > 10:
        return data
    
    if isinstance(data, dict):
        return {
            k: '***' if k.lower() in SENSITIVE_KEYS else mask_sensitive(v, depth + 1)
            for k, v in data.items()
        }
    elif isinstance(data, (list, tuple)):
        return type(data)(mask_sensitive(item, depth + 1) for item in data)
    return data


class StructuredFormatter(logging.Formatter):
    """
    结构化日志格式化器
    
    支持文本和 JSON 两种输出格式。
    """
    
    def __init__(self, fmt: str = None, datefmt: str = None, style: str = '%',
                 json_format: bool = False):
        super().__init__(fmt, datefmt, style)
        self.json_format = json_format
    
    def format(self, record: logging.LogRecord) -> str:
        record.asctime = self.formatTime(record, self.datefmt)
        
        if self.json_format:
            return self._format_json(record)
        return self._format_text(record)
    
    def _format_text(self, record: logging.LogRecord) -> str:
        base_msg = f"[{record.asctime}] [{record.levelname:8}] [{record.name}]"
        
        request_id = _request_id.get()
        if request_id:
            base_msg += f" [{request_id[:8]}]"
        
        message = record.getMessage()
        base_msg += f" {message}"
        
        if hasattr(record, 'extra_data') and record.extra_data:
            extra_str = json.dumps(mask_sensitive(record.extra_data), 
                                   ensure_ascii=False, default=str)
            base_msg += f" | {extra_str}"
        
        if record.exc_info:
            base_msg += f"\n{self.formatException(record.exc_info)}"
        
        return base_msg
    
    def _format_json(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': record.asctime,
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        request_id = _request_id.get()
        if request_id:
            log_data['request_id'] = request_id
        
        if hasattr(record, 'extra_data') and record.extra_data:
            log_data['data'] = mask_sensitive(record.extra_data)
        
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class LoggerAdapter(logging.LoggerAdapter):
    """
    日志适配器
    
    提供 extra 数据的便捷传递方法。
    """
    
    def process(self, msg: str, kwargs: Dict) -> tuple:
        extra = kwargs.get('extra', {})
        if 'extra_data' in extra:
            kwargs['extra']['extra_data'] = extra['extra_data']
        else:
            kwargs.setdefault('extra', {})['extra_data'] = {}
        return msg, kwargs
    
    def with_data(self, **kwargs) -> 'BoundLogger':
        return BoundLogger(self.logger, kwargs)


class BoundLogger:
    """
    绑定数据的日志器
    
    允许预先绑定数据，后续所有日志都会携带这些数据。
    """
    
    def __init__(self, logger: logging.Logger, data: Dict[str, Any]):
        self._logger = logger
        self._data = data
    
    def _log(self, level: int, msg: str, *args, **kwargs):
        extra = kwargs.get('extra', {})
        extra['extra_data'] = {**self._data, **extra.get('extra_data', {})}
        kwargs['extra'] = extra
        self._logger.log(level, msg, *args, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        self._log(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        self._log(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        self._log(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        self._log(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        self._log(logging.CRITICAL, msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs):
        kwargs.setdefault('exc_info', True)
        self._log(logging.ERROR, msg, *args, **kwargs)


class PerformanceMetrics:
    """
    性能指标收集器
    
    收集和存储性能指标数据。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._metrics = {}
                    cls._instance._timers = {}
        return cls._instance
    
    def start_timer(self, name: str) -> str:
        timer_id = f"{name}_{threading.current_thread().ident}_{time.time()}"
        self._timers[timer_id] = time.perf_counter()
        return timer_id
    
    def stop_timer(self, timer_id: str) -> float:
        if timer_id not in self._timers:
            return 0.0
        elapsed = time.perf_counter() - self._timers.pop(timer_id)
        return elapsed
    
    def record(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        if metric_name not in self._metrics:
            self._metrics[metric_name] = []
        self._metrics[metric_name].append({
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'tags': tags or {}
        })
        
        if len(self._metrics[metric_name]) > 1000:
            self._metrics[metric_name] = self._metrics[metric_name][-500:]
    
    def get_metrics(self, metric_name: str = None) -> Dict:
        if metric_name:
            return self._metrics.get(metric_name, [])
        return dict(self._metrics)
    
    def clear(self):
        self._metrics.clear()
        self._timers.clear()


metrics = PerformanceMetrics()


def timed(metric_name: str = None, tags: Dict[str, str] = None):
    """
    性能计时装饰器
    
    自动记录函数执行时间。
    
    Args:
        metric_name: 指标名称，默认使用函数名
        tags: 额外的标签
    
    Example:
        @timed('database_query', tags={'type': 'select'})
        def query_database():
            ...
    """
    def decorator(func: Callable) -> Callable:
        name = metric_name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            timer_id = metrics.start_timer(name)
            try:
                result = func(*args, **kwargs)
                elapsed = metrics.stop_timer(timer_id)
                metrics.record(name, elapsed, tags)
                return result
            except Exception as e:
                elapsed = metrics.stop_timer(timer_id)
                metrics.record(f"{name}.error", elapsed, tags)
                raise
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            timer_id = metrics.start_timer(name)
            try:
                result = await func(*args, **kwargs)
                elapsed = metrics.stop_timer(timer_id)
                metrics.record(name, elapsed, tags)
                return result
            except Exception as e:
                elapsed = metrics.stop_timer(timer_id)
                metrics.record(f"{name}.error", elapsed, tags)
                raise
        
        if asyncio and asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


try:
    import asyncio
except ImportError:
    asyncio = None


_loggers: Dict[str, LoggerAdapter] = {}
_handlers: list = []
_initialized = False


def setup_logging(
    level: str = None,
    log_dir: str = None,
    json_format: bool = False,
    max_size: int = 10,
    backup_count: int = 10,
    console_output: bool = True,
    console_level: str = None
) -> None:
    """
    初始化日志系统
    
    Args:
        level: 主日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        log_dir: 日志文件目录
        json_format: 是否使用 JSON 格式
        max_size: 单个日志文件最大大小 (MB)
        backup_count: 保留的日志文件数量
        console_output: 是否输出到控制台
        console_level: 控制台日志级别，默认与 level 相同
    """
    global _initialized, _handlers
    
    if _initialized:
        return
    
    log_level = getattr(logging, (level or os.environ.get('LOG_LEVEL', 'INFO')).upper())
    log_directory = Path(log_dir or os.environ.get('LOG_DIR', 'logs'))
    use_json = json_format or os.environ.get('LOG_FORMAT', 'text').lower() == 'json'
    max_bytes = int(os.environ.get('LOG_MAX_SIZE', max_size)) * 1024 * 1024
    backups = int(os.environ.get('LOG_BACKUP_COUNT', backup_count))
    console_lvl = getattr(logging, (console_level or level or 'INFO').upper())
    
    log_directory.mkdir(parents=True, exist_ok=True)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    for handler in _handlers:
        root_logger.removeHandler(handler)
    _handlers.clear()
    
    formatter = StructuredFormatter(
        datefmt='%Y-%m-%d %H:%M:%S',
        json_format=use_json
    )
    
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_lvl)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        _handlers.append(console_handler)
    
    file_handler = RotatingFileHandler(
        log_directory / 'app.log',
        maxBytes=max_bytes,
        backupCount=backups,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    _handlers.append(file_handler)
    
    error_handler = RotatingFileHandler(
        log_directory / 'error.log',
        maxBytes=max_bytes,
        backupCount=backups,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    _handlers.append(error_handler)
    
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    _initialized = True


def get_logger(name: str = None) -> LoggerAdapter:
    """
    获取日志器
    
    Args:
        name: 模块名称，通常使用 __name__
    
    Returns:
        LoggerAdapter 实例
    
    Example:
        logger = get_logger(__name__)
        logger.info("操作完成")
    """
    if not _initialized:
        setup_logging()
    
    logger_name = name or 'app'
    
    if logger_name not in _loggers:
        base_logger = logging.getLogger(logger_name)
        _loggers[logger_name] = LoggerAdapter(base_logger, {})
    
    return _loggers[logger_name]


def set_request_id(request_id: str = None) -> str:
    """
    设置请求追踪 ID
    
    Args:
        request_id: 自定义请求 ID，不提供则自动生成
    
    Returns:
        设置的请求 ID
    """
    if request_id is None:
        request_id = f"{time.time():.6f}_{threading.current_thread().ident}"
    _request_id.set(request_id)
    return request_id


def clear_request_id() -> None:
    """清除请求追踪 ID"""
    _request_id.set(None)


def log_function_call(logger: LoggerAdapter = None):
    """
    函数调用日志装饰器
    
    记录函数的调用参数和返回值。
    
    Example:
        @log_function_call()
        def my_function(a, b):
            return a + b
    """
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(
                f"调用函数: {func.__name__}",
                extra={'extra_data': {
                    'args': mask_sensitive(args[:3]) if args else [],
                    'kwargs': mask_sensitive(kwargs)
                }}
            )
            try:
                result = func(*args, **kwargs)
                logger.debug(
                    f"函数返回: {func.__name__}",
                    extra={'extra_data': {'result_type': type(result).__name__}}
                )
                return result
            except Exception as e:
                logger.error(
                    f"函数异常: {func.__name__}",
                    extra={'extra_data': {
                        'exception_type': type(e).__name__,
                        'exception_message': str(e)
                    }},
                    exc_info=True
                )
                raise
        
        return wrapper
    return decorator


class ConsoleLogger:
    """
    控制台输出器
    
    用于启动脚本等需要直接输出到控制台的场景。
    同时输出到控制台和日志系统。
    """
    
    def __init__(self, name: str = 'console'):
        self._logger = get_logger(name)
        self._name = name
    
    def _output(self, level: str, message: str, **kwargs):
        print(message, **kwargs)
        log_method = getattr(self._logger, level, self._logger.info)
        clean_msg = message.replace('✓', '[OK]').replace('⚠', '[WARN]').replace('❌', '[ERR]').replace('🚀', '[START]')
        log_method(clean_msg)
    
    def info(self, message: str, **kwargs):
        self._output('info', message, **kwargs)
    
    def success(self, message: str, **kwargs):
        self._output('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._output('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._output('error', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        if os.environ.get('DEBUG'):
            self._output('debug', message, **kwargs)
    
    def separator(self, char: str = '=', length: int = 60):
        line = char * length
        print(line)
    
    def section(self, title: str):
        self.separator()
        print(title)
        self.separator()


console = ConsoleLogger()
