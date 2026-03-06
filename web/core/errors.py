"""
统一错误处理
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
    """错误码定义"""
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
    """注册全局错误处理器"""
    
    @app.errorhandler(VideoNotFoundError)
    def handle_video_not_found(error):
        return APIResponse.error(
            message=str(error),
            error_code=ErrorCode.VIDEO_NOT_FOUND,
            details=error.details,
            status_code=404
        )
    
    @app.errorhandler(TagNotFoundError)
    def handle_tag_not_found(error):
        return APIResponse.error(
            message=str(error),
            error_code=ErrorCode.TAG_NOT_FOUND,
            details=error.details,
            status_code=404
        )
    
    @app.errorhandler(DuplicateVideoError)
    def handle_duplicate_video(error):
        return APIResponse.error(
            message=str(error),
            error_code=ErrorCode.DUPLICATE_VIDEO,
            details=error.details,
            status_code=409
        )
    
    @app.errorhandler(DuplicateTagError)
    def handle_duplicate_tag(error):
        return APIResponse.error(
            message=str(error),
            error_code=ErrorCode.DUPLICATE_TAG,
            details=error.details,
            status_code=409
        )
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return APIResponse.error(
            message=str(error),
            error_code=ErrorCode.VALIDATION_ERROR,
            details=error.details,
            status_code=422
        )
    
    @app.errorhandler(DatabaseError)
    def handle_database_error(error):
        return APIResponse.error(
            message="数据库操作失败",
            error_code=ErrorCode.DATABASE_ERROR,
            status_code=500
        )
    
    @app.errorhandler(VideoTagSystemError)
    def handle_system_error(error):
        return APIResponse.error(
            message=str(error),
            error_code=ErrorCode.UNKNOWN_ERROR,
            details=error.details,
            status_code=500
        )
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        return APIResponse.error(
            message="请求格式错误",
            error_code=ErrorCode.BAD_REQUEST,
            status_code=400
        )
    
    @app.errorhandler(404)
    def handle_not_found(error):
        if request.path.startswith('/api/'):
            return APIResponse.error(
                message="API端点不存在",
                error_code=ErrorCode.NOT_FOUND,
                status_code=404
            )
        return jsonify({'error': '页面不存在'}), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        return APIResponse.error(
            message="服务器内部错误",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500
        )
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        traceback.print_exc()
        return APIResponse.error(
            message="发生未知错误",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500
        )


def handle_exceptions(f):
    """异常处理装饰器，用于捕获并统一处理异常"""
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
