"""
统一错误处理模块

提供全局错误处理器和异常处理装饰器。

主要功能：
    - ErrorCode: 错误码定义类
    - register_error_handlers: 注册全局错误处理器
    - handle_exceptions: 异常处理装饰器

错误码说明：
    - UNKNOWN_ERROR: 未知错误
    - VIDEO_NOT_FOUND: 视频不存在
    - TAG_NOT_FOUND: 标签不存在
    - DUPLICATE_VIDEO: 视频重复
    - DUPLICATE_TAG: 标签重复
    - DATABASE_ERROR: 数据库错误
    - VALIDATION_ERROR: 验证错误
    - TAG_MERGE_ERROR: 标签合并错误
    - BACKUP_ERROR: 备份错误
    - UNAUTHORIZED: 未授权
    - FORBIDDEN: 禁止访问
    - NOT_FOUND: 资源不存在
    - BAD_REQUEST: 请求格式错误

使用示例：
    # 注册错误处理器
    from web.core.errors import register_error_handlers
    register_error_handlers(app)
    
    # 使用装饰器
    from web.core.errors import handle_exceptions
    
    @app.route('/api/example')
    @handle_exceptions
    def example():
        # 业务逻辑
        pass

HTTP状态码映射：
    - 400: 请求格式错误
    - 401: 未授权
    - 403: 禁止访问
    - 404: 资源不存在
    - 409: 资源冲突
    - 422: 验证失败
    - 500: 服务器错误
"""
import traceback
from functools import wraps
from flask import jsonify, request, Response
from video_tag_system.exceptions import (
    VideoTagSystemError,
    VideoNotFoundError,
    TagNotFoundError,
    DuplicateVideoError,
    DuplicateTagError,
    DatabaseError,
    ValidationError,
    TagMergeError,
    BackupError
)
from web.core.responses import APIResponse


class ErrorCode:
    """
    错误码定义类
    
    定义系统中使用的所有错误码，用于客户端识别错误类型。
    
    Attributes:
        UNKNOWN_ERROR: 未知错误
        VIDEO_NOT_FOUND: 视频不存在
        TAG_NOT_FOUND: 标签不存在
        DUPLICATE_VIDEO: 视频重复
        DUPLICATE_TAG: 标签重复
        DATABASE_ERROR: 数据库错误
        VALIDATION_ERROR: 验证错误
        TAG_MERGE_ERROR: 标签合并错误
        BACKUP_ERROR: 备份错误
        UNAUTHORIZED: 未授权
        FORBIDDEN: 禁止访问
        NOT_FOUND: 资源不存在
        BAD_REQUEST: 请求格式错误
    """
    
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VIDEO_NOT_FOUND = "VIDEO_NOT_FOUND"
    TAG_NOT_FOUND = "TAG_NOT_FOUND"
    DUPLICATE_VIDEO = "DUPLICATE_VIDEO"
    DUPLICATE_TAG = "DUPLICATE_TAG"
    DATABASE_ERROR = "DATABASE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TAG_MERGE_ERROR = "TAG_MERGE_ERROR"
    BACKUP_ERROR = "BACKUP_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    BAD_REQUEST = "BAD_REQUEST"


def register_error_handlers(app):
    """
    注册全局错误处理器
    
    为Flask应用注册所有异常和HTTP错误的处理器。
    处理器会将错误转换为统一的JSON响应格式。
    
    Args:
        app: Flask应用实例
    
    处理的异常类型：
        - VideoNotFoundError: 视频不存在 (404)
        - TagNotFoundError: 标签不存在 (404)
        - DuplicateVideoError: 视频重复 (409)
        - DuplicateTagError: 标签重复 (409)
        - ValidationError: 验证错误 (422)
        - DatabaseError: 数据库错误 (500)
        - VideoTagSystemError: 系统错误 (500)
        - 400: 请求格式错误
        - 404: 资源不存在
        - 500: 服务器内部错误
        - Exception: 未捕获的异常
    """
    
    @app.errorhandler(VideoNotFoundError)
    def handle_video_not_found(error):
        """处理视频不存在错误"""
        return APIResponse.error(
            message=str(error),
            error_code=ErrorCode.VIDEO_NOT_FOUND,
            details=error.details,
            status_code=404
        )
    
    @app.errorhandler(TagNotFoundError)
    def handle_tag_not_found(error):
        """处理标签不存在错误"""
        return APIResponse.error(
            message=str(error),
            error_code=ErrorCode.TAG_NOT_FOUND,
            details=error.details,
            status_code=404
        )
    
    @app.errorhandler(DuplicateVideoError)
    def handle_duplicate_video(error):
        """处理视频重复错误"""
        return APIResponse.error(
            message=str(error),
            error_code=ErrorCode.DUPLICATE_VIDEO,
            details=error.details,
            status_code=409
        )
    
    @app.errorhandler(DuplicateTagError)
    def handle_duplicate_tag(error):
        """处理标签重复错误"""
        return APIResponse.error(
            message=str(error),
            error_code=ErrorCode.DUPLICATE_TAG,
            details=error.details,
            status_code=409
        )
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """处理验证错误"""
        return APIResponse.error(
            message=str(error),
            error_code=ErrorCode.VALIDATION_ERROR,
            details=error.details,
            status_code=422
        )
    
    @app.errorhandler(DatabaseError)
    def handle_database_error(error):
        """处理数据库错误"""
        return APIResponse.error(
            message="数据库操作失败",
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=500
        )
    
    @app.errorhandler(VideoTagSystemError)
    def handle_system_error(error):
        """处理系统错误"""
        return APIResponse.error(
            message=str(error),
            error_code=ErrorCode.UNKNOWN_ERROR,
            details=error.details,
            status_code=500
        )
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        """处理请求格式错误"""
        return APIResponse.error(
            message="请求格式错误",
            error_code=ErrorCode.BAD_REQUEST,
            status_code=400
        )
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """处理资源不存在错误"""
        if request.path.startswith('/api/'):
            return APIResponse.error(
                message="API端点不存在",
                error_code=ErrorCode.NOT_FOUND,
                status_code=404
            )
        return jsonify({'error': '页面不存在'}), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """处理服务器内部错误"""
        return APIResponse.error(
            message="服务器内部错误",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500
        )
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """处理未捕获的异常"""
        traceback.print_exc()
        return APIResponse.error(
            message="发生未知错误",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500
        )


def handle_exceptions(f):
    """
    异常处理装饰器
    
    捕获函数中抛出的异常并转换为统一的API响应格式。
    适用于单个路由函数的异常处理。
    
    Args:
        f: 被装饰的函数
    
    Returns:
        装饰后的函数
    
    Example:
        @app.route('/api/videos/<int:video_id>')
        @handle_exceptions
        def get_video(video_id):
            video = video_service.get_video(video_id)
            return APIResponse.success(data=video)
    
    Note:
        此装饰器会捕获以下异常：
        - VideoNotFoundError -> 404
        - TagNotFoundError -> 404
        - ValidationError -> 422
        - VideoTagSystemError -> 500
        - Exception -> 500（打印堆栈跟踪）
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except VideoNotFoundError as e:
            return APIResponse.error(
                message=str(e),
                error_code=ErrorCode.VIDEO_NOT_FOUND,
                details=e.details,
                status_code=404
            )
        except TagNotFoundError as e:
            return APIResponse.error(
                message=str(e),
                error_code=ErrorCode.TAG_NOT_FOUND,
                details=e.details,
                status_code=404
            )
        except ValidationError as e:
            return APIResponse.error(
                message=str(e),
                error_code=ErrorCode.VALIDATION_ERROR,
                details=e.details,
                status_code=422
            )
        except VideoTagSystemError as e:
            return APIResponse.error(
                message=str(e),
                error_code=ErrorCode.UNKNOWN_ERROR,
                details=e.details,
                status_code=500
            )
        except Exception as e:
            traceback.print_exc()
            return APIResponse.server_error(str(e))
    return decorated_function
