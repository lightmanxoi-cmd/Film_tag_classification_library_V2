"""
统一API响应格式
"""
from typing import Any, Optional, Dict
from flask import jsonify, Response


class APIResponse:
    """统一API响应格式类"""
    
    @staticmethod
    def success(data: Any = None, message: str = "操作成功", cached: bool = False, status_code: int = 200) -> Response:
        """成功响应"""
        response = {
            'success': True,
            'message': message,
            'data': data,
            'cached': cached
        }
        return jsonify(response), status_code
    
    @staticmethod
    def error(message: str, error_code: str = None, details: Optional[Dict] = None, status_code: int = 400) -> Response:
        """错误响应"""
        response = {
            'success': False,
            'error': message,
        }
        if error_code:
            response['error_code'] = error_code
        if details:
            response['details'] = details
        return jsonify(response), status_code
    
    @staticmethod
    def paginated(
        items: list,
        total: int,
        page: int,
        page_size: int,
        cached: bool = False
    ) -> Response:
        """分页响应"""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        data = {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        }
        return APIResponse.success(data=data, cached=cached)
    
    @staticmethod
    def created(data: Any = None, message: str = "创建成功") -> Response:
        """创建成功响应"""
        return APIResponse.success(data=data, message=message, status_code=201)
    
    @staticmethod
    def no_content() -> Response:
        """无内容响应"""
        return jsonify({}), 204
    
    @staticmethod
    def unauthorized(message: str = "未授权访问，请先登录", timeout: bool = False) -> Response:
        """未授权响应"""
        response = {
            'success': False,
            'error': message,
        }
        if timeout:
            response['timeout'] = True
        return jsonify(response), 401
    
    @staticmethod
    def forbidden(message: str = "禁止访问") -> Response:
        """禁止访问响应"""
        return APIResponse.error(message=message, status_code=403)
    
    @staticmethod
    def not_found(message: str = "资源不存在") -> Response:
        """资源不存在响应"""
        return APIResponse.error(message=message, status_code=404)
    
    @staticmethod
    def validation_error(field: str, reason: str) -> Response:
        """验证错误响应"""
        return APIResponse.error(
            message=f"验证失败 - 字段 '{field}': {reason}",
            error_code='VALIDATION_ERROR',
            details={'field': field, 'reason': reason},
            status_code=422
        )
    
    @staticmethod
    def server_error(message: str = "服务器内部错误") -> Response:
        """服务器错误响应"""
        return APIResponse.error(message=message, status_code=500)
